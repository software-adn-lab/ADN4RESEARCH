import logging
from apps.design.search_strategy.models.keyword import Keyword, ProjectKeyword
from apps.design.search_strategy.models.search_strategy import SearchStrategy, SearchStrategyVersion
from django.db.models import Max
from django.db import transaction
from apps.acquisition.facade import get_acquisition_facade


class SearchStrategyService:
    @transaction.atomic
    def generate_and_save_search_string(self, strategy_id: int, user_id: int = None) -> SearchStrategy:
        strategy = SearchStrategy.objects.select_related('research_question').get(id=strategy_id)
        keywords = list(strategy.keywords.select_related('project_keyword').all())
        exclusions = list(strategy.exclusion_terms.all())
        json_definition = self._build_json_definition(keywords, exclusions)
        final_search_string = self._build_boolean_string(keywords, exclusions)

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

    def _build_boolean_string(self, keywords: list, exclusions: list) -> str:
        if not keywords:
            return ""
        or_groups = []
        for kw in keywords:
            pk = kw.project_keyword
            terms_in_group = [f'"{pk.term}"']
            
            synonyms_list = self._parse_synonyms(pk.synonyms)
            for syn in synonyms_list:
                terms_in_group.append(f'"{syn}"')
            group_string = " OR ".join(terms_in_group)
            or_groups.append(f"({group_string})")
        final_string = " AND ".join(or_groups)
        if exclusions:
            exclusion_terms = [f'"{exc.term}"' for exc in exclusions]
            exclusion_string = " OR ".join(exclusion_terms)
            final_string += f" AND NOT ({exclusion_string})"
        return final_string

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

    # TRABAJO PARA SUGERIDOS SIN SINONIMOS Y CON SINONIMOS
    def _link_project_keywords_to_strategy(self, strategy: SearchStrategy, keyword_data: list[dict], clear_previous: bool = True):
        design_phase_id = strategy.research_question.design_phase_id
        with transaction.atomic():
            if clear_previous:
                strategy.keywords.all().delete()

            keywords_to_link = []
            for item in keyword_data:
                term_text = item.get('term')
                if not term_text:
                    continue
                project_keyword, created = ProjectKeyword.objects.update_or_create(
                    design_phase_id=design_phase_id, 
                    term=term_text,
                    defaults={
                        'synonyms': item.get('synonyms', '')
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

    # SOLO PARA LO SUGERIDO (SIN SINONIMOS)
    def populate_strategy_from_structured_data(self, strategy_id: int, keyword_data: list[dict]):
        strategy = SearchStrategy.objects.select_related('research_question').get(id=strategy_id)
        self._link_project_keywords_to_strategy(strategy, keyword_data)

    def sync_suggested_terms_with_strategy(self, research_question_id: int, suggested_terms: list[str]) -> SearchStrategy:
        strategy = self._get_or_create_strategy(research_question_id)
        keyword_data = [{'term': term, 'synonyms': ''} for term in suggested_terms]
        self._link_project_keywords_to_strategy(strategy, keyword_data)
        return strategy
    
    def get_strategy_for_question(self, question_id: int) -> SearchStrategy | None:
        return SearchStrategy.objects.filter(research_question_id=question_id).first()
    
    def create_or_update_strategy_with_keywords(self, research_question_id: int, keyword_data: list[dict], user=None) -> SearchStrategy:
        strategy = self._get_or_create_strategy(research_question_id)
        self._link_project_keywords_to_strategy(strategy, keyword_data)
        if user:
            strategy.last_modified_by = user
            strategy.save(update_fields=['last_modified_by'])
        return strategy

    def get_or_create_strategy(self, research_question_id: int) -> SearchStrategy:
        return self._get_or_create_strategy(research_question_id)
    
    def get_strategy_by_id(self, strategy_id: int) -> SearchStrategy:
        return SearchStrategy.objects.select_related('research_question__design_phase__project').get(id=strategy_id)
    
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
        strategy = SearchStrategy.objects.get(id=strategy_id)
        strategy.json_definition = visual_data
        strategy.final_search_string = self._build_string_from_json(visual_data)
        strategy.status = SearchStrategy.Status.DRAFT
        strategy.last_modified_by_id = user_id
        strategy.save()
        acquisition_facade = get_acquisition_facade()
        logging.info(f"Fetching search preview for strategy ID {visual_data}")
        
        try:
            preview_result = acquisition_facade.preview_search(visual_data)
            count = getattr(preview_result, 'total_found', 0) 
            
        except Exception as e:
            print(f"Error fetching search preview: {e}")
            count = 0
        self.create_version_snapshot(strategy.id, user_id, total_found=count)
        
        return strategy

    def _build_string_from_json(self, data: dict) -> str:
        main_terms = data.get('main_terms', [])
        exclusions = data.get('exclusions', [])
        and_blocks = []
        for group in main_terms:
            term = group.get('term', '').strip()
            synonyms = group.get('synonyms', [])
            if not term: continue
            all_terms = [f'"{term}"'] + [f'"{s.strip()}"' for s in synonyms if s.strip()]
            block_str = " OR ".join(all_terms)
            and_blocks.append(f"({block_str})")
        search_string = " AND ".join(and_blocks)
        if exclusions:
            not_terms = [f'"{exc.strip()}"' for exc in exclusions if exc.strip()]
            if not_terms:
                not_block = " OR ".join(not_terms)
                search_string += f" AND NOT ({not_block})"
                
        return search_string
    
    def get_search_results_dto(self, strategy_id: int):
        strategy = self.get_or_create_strategy(strategy_id)
        acquisition_facade = get_acquisition_facade()
        try:
            results_dto = acquisition_facade.preview_search(strategy.json_definition)
            return results_dto
        except Exception as e:
            raise RuntimeError(f"Error fetching search results: {e}")
    
    def change_strategy_status(self, strategy_id: int, status: str, user) -> SearchStrategy:
        strategy = SearchStrategy.objects.get(id=strategy_id)
        strategy.status = status
        strategy.last_modified_by = user
        if status == SearchStrategy.Status.APPROVED:
             strategy.reviewed_by = user
        
        strategy.save()
        return strategy
            