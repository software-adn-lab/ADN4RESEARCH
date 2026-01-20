import logging
from apps.design.search_strategy.models.keyword import Keyword, ProjectKeyword
from apps.design.search_strategy.models.search_strategy import SearchStrategy, SearchStrategyVersion
from django.db.models import Max
from django.db import transaction
from googletrans import Translator
from asgiref.sync import async_to_sync

from apps.design.search_strategy.services.search_string_builder import SearchStringBuilder
from apps.design.research_question.models.research_question import ResearchQuestion
from apps.design.design_phase_logic.models.design_phase import DesignPhase
from django.core.exceptions import ValidationError
from apps.design.access_control import DesignAccessPolicy
from django.contrib.auth.models import User
from apps.design.search_strategy.services.search_preview_service import SearchPreviewService
from apps.design.search_strategy.services.nlp.translation_service import TranslationService


class SearchStrategyService:
    def __init__(self):
        self.string_builder = SearchStringBuilder()
        self.preview_service = SearchPreviewService()
        self.translation_service = TranslationService()

    @transaction.atomic
    def generate_and_save_search_string(self, strategy_id: int, user_id: int) -> SearchStrategy:
        strategy = SearchStrategy.objects.select_related('research_question').get(id=strategy_id)
        keywords = list(strategy.keywords.select_related('project_keyword').all())
        exclusions = list(strategy.exclusion_terms.all())
        json_definition = self._build_json_definition(keywords, exclusions)
        final_search_string = self.string_builder.build_from_json(json_definition)
        if strategy.final_search_string == final_search_string and strategy.json_definition == json_definition:
            return strategy

        if user_id:
            strategy.last_modified_by_id = user_id

        strategy.json_definition = json_definition
        strategy.final_search_string = final_search_string
        strategy.save()
        self.create_version_snapshot(strategy_id=strategy.id, user_id=user_id)

        return strategy

    def get_version_by_id(self, version_id: int) -> SearchStrategyVersion:
        return SearchStrategyVersion.objects.get(id=version_id)

    def _build_json_definition(self, keywords: list, exclusions: list) -> dict:
        json_main_terms = []
        for kw in keywords:
            pk = kw.project_keyword
            synonyms_list = self._parse_synonyms(pk.synonyms)

            json_main_terms.append({
                "term": pk.term,
                "synonyms": synonyms_list
            })

        json_exclusions = [exc.term for exc in exclusions]

        return {
            "main_terms": json_main_terms,
            "exclusions": json_exclusions
        }

    def _parse_synonyms(self, synonyms_str: str) -> list[str]:
        if not synonyms_str or not synonyms_str.strip():
            return []
        return [s.strip() for s in synonyms_str.split(',') if s.strip()]

    def _get_or_create_strategy(self, research_question_id: int) -> SearchStrategy:
        strategy, _ = SearchStrategy.objects.update_or_create(
            research_question_id=research_question_id,
            defaults={
                'status': SearchStrategy.Status.DRAFT
            }
        )
        return strategy

    def delete_strategy_version(self, version_id: int):
        version = SearchStrategyVersion.objects.get(id=version_id)
        version.delete()

    def _update_strategy_keywords(self, strategy: SearchStrategy, keyword_data: list[dict], clear_previous: bool = True):
        """
        Updates the keywords associated with a search strategy.
        :param strategy: The SearchStrategy instance.
        :param keyword_data: List of dicts with 'term' and optional 'synonyms'.
        :param clear_previous: If True, removes existing keywords before adding new ones.
        """
        design_phase_id = strategy.research_question.design_phase_id
        with transaction.atomic():
            if clear_previous:
                strategy.keywords.all().delete()

            keywords_to_link = []
            for item in keyword_data:
                term_text = item.get('term')
                if not term_text:
                    continue

                # TRANSLATE term and synonyms from ES to EN before saving
                synonyms_text = item.get('synonyms', '')
                translated_term = self._translate_text(term_text)
                translated_synonyms = self._translate_text(synonyms_text) if synonyms_text else ''

                project_keyword, created = ProjectKeyword.objects.update_or_create(
                    design_phase_id=design_phase_id,
                    term=translated_term,
                    defaults={
                        'synonyms': translated_synonyms
                    }
                )
                if not clear_previous:
                    if Keyword.objects.filter(strategy=strategy, project_keyword=project_keyword).exists():
                        continue
                keywords_to_link.append(
                    Keyword(strategy=strategy, project_keyword=project_keyword)
                )
            if keywords_to_link:
                Keyword.objects.bulk_create(keywords_to_link, ignore_conflicts=True)

    def sync_suggested_terms_with_strategy(self, research_question_id: int, suggested_terms: list[str]) -> SearchStrategy:
        """
        Syncs suggested terms from NLP service to the strategy.
        """
        strategy = self._get_or_create_strategy(research_question_id)
        keyword_data = [{'term': term, 'synonyms': ''} for term in suggested_terms]
        self._update_strategy_keywords(strategy, keyword_data)
        return strategy

    def create_or_update_strategy_with_keywords(self, research_question_id: int, keyword_data: list[dict], user: User) -> SearchStrategy:
        strategy = self._get_or_create_strategy(research_question_id)
        self._update_strategy_keywords(strategy, keyword_data)
        if user:
            strategy.last_modified_by = user
            strategy.save(update_fields=['last_modified_by'])
        return strategy

    def get_or_create_strategy(self, research_question_id: int) -> SearchStrategy:
        return self._get_or_create_strategy(research_question_id)

    # get_strategy_by_id moved to Selector
    # get_strategy_for_question moved to Selector

    def get_or_create_project_keyword(self, project_id: int, term: str, synonyms: str) -> ProjectKeyword:
        keyword, created = ProjectKeyword.objects.update_or_create(
            design_phase_id=project_id,
            term=term,
            defaults={
                'synonyms': synonyms
            }
        )
        return keyword

    # Metodo del patron para crear el memento.
    def create_version_snapshot(self, strategy_id: int, user_id: int | None, total_found: int = 0) -> int:
        strategy = SearchStrategy.objects.get(id=strategy_id)
        last_version = strategy.versions.aggregate(Max('version_number'))['version_number__max']
        new_version_number = 1 if last_version is None else last_version + 1

        current_keywords = [k.project_keyword.term for k in strategy.keywords.select_related('project_keyword')]
        current_exclusions = [e.term for e in strategy.exclusion_terms.all()]

        snapshot_data = {
            'keywords': current_keywords,
            'exclusions': current_exclusions,
        }

        SearchStrategyVersion.objects.create(
            strategy=strategy,
            version_number=new_version_number,
            final_search_string=strategy.final_search_string,
            json_definition=strategy.json_definition,
            metadata_snapshot=snapshot_data,
            total_found=total_found,
            created_by_id=user_id
        )
        return new_version_number

    @transaction.atomic
    def save_strategy_from_visual_builder(self, strategy_id: int, visual_data: dict, user_id: int) -> SearchStrategy:
        strategy = SearchStrategy.objects.select_related('research_question__design_phase__project').get(id=strategy_id)
        user = User.objects.get(id=user_id)

        # Authorization Check (Edit)
        if not DesignAccessPolicy.can_edit_strategy(user, strategy):
            raise ValidationError("You do not have permission to edit this strategy.")

        # Check if need to notify before updating
        should_notify = self._should_notify_owner_modification(strategy, user)

        new_search_string = self.string_builder.build_from_json(visual_data)
        if strategy.final_search_string == new_search_string and strategy.json_definition == visual_data:
            return strategy
        strategy.json_definition = visual_data
        strategy.final_search_string = new_search_string
        strategy.status = SearchStrategy.Status.DRAFT
        strategy.last_modified_by_id = user_id
        strategy.save()

        count = self.preview_service.translate_and_preview(visual_data)
        self.create_version_snapshot(strategy.id, user_id, total_found=count)

        # Notify after successful update
        if should_notify:
            self._notify_if_owner_action_in_closed_stage(strategy, user)

        return strategy

    def get_search_results_dto(self, strategy_id: int):
        strategy = SearchStrategy.objects.get(id=strategy_id)
        return self.preview_service.get_search_results_dto(strategy)

    def change_strategy_status(self, strategy_id: int, status: str, user: User, justification: str = None) -> SearchStrategy:
        strategy = SearchStrategy.objects.select_related('research_question__design_phase__project').get(id=strategy_id)

        # Authorization Check (Review)
        if status in [SearchStrategy.Status.APPROVED, SearchStrategy.Status.REJECTED]:
            if not DesignAccessPolicy.can_review_strategy(user, strategy.research_question.design_phase):
                raise ValidationError("You do not have permission to review strategies.")

        strategy.status = status
        strategy.last_modified_by = user
        if status == SearchStrategy.Status.APPROVED:
            strategy.reviewed_by = user

        strategy.save()

        latest_version = strategy.versions.first()
        if latest_version:
            latest_version.status = status
            if justification:
                latest_version.justification = justification
            latest_version.save(update_fields=['status', 'justification'])

        return strategy

    @transaction.atomic
    def finalize_strategies_stage(self, project_id: int, user: User) -> dict:
        # Authorization is handled by DesignPhaseService.consolidate_search_strategy_stage calling this.
        # But we can add a check here too if needed.

        approved_questions = ResearchQuestion.objects.filter(
            design_phase_id=project_id,
            status=ResearchQuestion.Status.APPROVED
        )
        for question in approved_questions:
            if not SearchStrategy.objects.filter(research_question=question).exists():
                raise ValidationError(f"Research Question '{question.question[:50]}...' does not have a search strategy defined.")
        approved_ids = []
        strategies = SearchStrategy.objects.filter(research_question__design_phase_id=project_id)

        for strategy in strategies:
            strategy.versions.filter(status=SearchStrategy.Status.DRAFT).update(status=SearchStrategy.Status.REJECTED)
            if strategy.status == SearchStrategy.Status.APPROVED:
                approved_ids.append(strategy.id)

        if not approved_ids:
            raise ValidationError("At least one search strategy must be approved to consolidate the stage.")

        return approved_ids

    def _should_notify_owner_modification(self, strategy: SearchStrategy, user: User) -> bool:
        """Check if we should notify about owner modification in closed stage."""
        design_phase = strategy.research_question.design_phase
        project = design_phase.project
        
        # Only notify if user is owner
        if not DesignAccessPolicy.is_owner(user, project):
            return False
        
        # Only notify if stage is closed
        if design_phase.current_stage == design_phase.DesignStage.SEARCH_STRATEGY:
            return False
        
        # Only notify if strategy is approved
        if strategy.status != SearchStrategy.Status.APPROVED:
            return False
        
        return True

    def _notify_if_owner_action_in_closed_stage(self, strategy: SearchStrategy, user: User):
        """Send notification if owner modifies strategy in closed stage."""
        design_phase = strategy.research_question.design_phase
        project = design_phase.project
        
        # Only notify if owner
        if not DesignAccessPolicy.is_owner(user, project):
            return
        
        # Only notify if stage is closed
        if design_phase.current_stage == design_phase.DesignStage.SEARCH_STRATEGY:
            return
        
        # Only notify if approved
        if strategy.status != SearchStrategy.Status.APPROVED:
            return
        
        try:
            from apps.notification.models import Notification
            from apps.project.api.providers import ProjectManagementProvider
            
            provider = ProjectManagementProvider()
            members = provider.get_project_member_users(project.id)
            
            for member in members:
                Notification.objects.create(
                    recipient=member,
                    sender=user,
                    type='OWNER_MODIFIED_APPROVED_STRATEGY',
                    title='Owner modified search strategy in closed stage',
                    custom_message=f'The project owner has modified an approved search strategy in a closed stage. Please review the changes for audit purposes.',
                    project=project
                )
        except Exception:
            pass  # Silent fail on notification errors

    def _translate_text(self, text: str) -> str:
        """
        Helper method to translate a single text string from Spanish to English.
        Uses TranslationService with async_to_sync for individual translation.
        Returns original text if translation fails.
        """
        if not text or not text.strip():
            return text

        try:
            async def _do_translate():
                translator = Translator()
                result = await translator.translate(text, src='es', dest='en')
                return result.text

            return async_to_sync(_do_translate)()
        except Exception as e:
            logging.error(f"Translation error for '{text}': {e}")
            return text  # Fallback to original text if translation fails
