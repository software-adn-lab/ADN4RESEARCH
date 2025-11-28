import logging
from apps.design.search_strategy.models.keyword import Keyword, ProjectKeyword
from apps.design.search_strategy.models.search_strategy import SearchStrategy, SearchStrategyVersion
from django.db.models import Max
from django.db import transaction


class SearchStrategyService:
    def generate_and_save_search_string(self, strategy_id, user_id=None) -> SearchStrategy:
        strategy = SearchStrategy.objects.select_related('research_question').get(id=strategy_id)
        keywords = strategy.keywords.select_related('project_keyword').all()
        
        if not keywords:
            strategy.final_search_string = ""
            strategy.save()
            return strategy
        or_groups = []
        for kw in keywords:
            pk = kw.project_keyword
            terms = [f'"{pk.term}"']
            if pk.synonyms and pk.synonyms.strip():
                synonyms_list = [s.strip() for s in pk.synonyms.split(',')]
                for s in synonyms_list:
                    if s:
                        terms.append(f'"{s}"')
            group_string = ' OR '.join(terms)
            or_groups.append(f"({group_string})")
        final_string = " AND ".join(or_groups)

        strategy.final_search_string = final_string
        strategy.save()
        self.create_version_snapshot(strategy_id= strategy.id, user_id=user_id)  # user_id puede ser None por la sugerencia automática
        return strategy
    
    def _get_or_create_strategy(self, research_question_id: int) -> SearchStrategy:
        strategy, _ = SearchStrategy.objects.update_or_create(
            research_question_id=research_question_id,
            defaults={
                'name': f"Suggested Strategy for Question {research_question_id}",
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
                project_keyword, _ = ProjectKeyword.objects.get_or_create(
                    design_phase_id=design_phase_id, 
                    term=term_text,
                    defaults={'synonyms': item.get('synonyms', '')}
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
    
    def create_or_update_strategy_with_keywords(self, research_question_id: int, keyword_data: list[dict]) -> SearchStrategy:
        # 1. Obtener o crear la estrategia para asegurar que siempre exista.
        strategy = self._get_or_create_strategy(research_question_id)
        # 2. Llamar al método central para limpiar los keywords antiguos y enlazar los nuevos.
        self._link_project_keywords_to_strategy(strategy, keyword_data)
        return strategy

    # Metodo del patron para crear el memento.
    def create_version_snapshot(self, strategy_id: int, user_id: int | None) -> int: # El None es por la sugerencia automática del sistema jeje
        strategy = SearchStrategy.objects.get(id=strategy_id)
        last_version = strategy.versions.aggregate(Max('version_number'))['version_number__max']
        new_version_number = 1 if last_version is None else last_version + 1

        # Estas son las cosas que se guardan en el momento del checkpoint
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
            metadata_snapshot=snapshot_data,
            created_by_id=user_id
        )
        return new_version_number