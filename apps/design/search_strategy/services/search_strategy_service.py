import logging
from apps.design.search_strategy.models.keyword import Keyword, ProjectKeyword
from apps.design.search_strategy.models.search_strategy import SearchStrategy
from apps.project.models import Project
from apps.design.research_question.models.research_question import ResearchQuestion


class SearchStrategyService:
    def generate_and_save_search_string(self, strategy_id) -> SearchStrategy:
        strategy = SearchStrategy.objects.select_related('research_question').get(id=strategy_id)
        keywords = strategy.keywords.select_related('project_keyword').all()
        
        if not keywords:
            strategy.final_search_string = ""
            strategy.save()
            return strategy
        or_groups = []
        for kw in keywords:
            # Acceder a los datos a través del objeto project_keyword relacionado
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
    def _link_project_keywords_to_strategy(self, strategy: SearchStrategy, keyword_data: list[dict]):
        project_id = strategy.research_question.project_id
        # 1. Limpiar keywords antiguos de la estrategia
        strategy.keywords.all().delete()
        # 2. Preparar los nuevos keywords para el bulk_create
        keywords_to_link = []
        for item in keyword_data:
            term = item.get('term')
            if not term:
                continue

            project_keyword, _ = ProjectKeyword.objects.get_or_create(
                project_id=project_id,
                term=term,
                defaults={'synonyms': item.get('synonyms', '')}
            )
            
            keywords_to_link.append(
                Keyword(strategy_id=strategy.id, project_keyword_id=project_keyword.id)
            )
        if keywords_to_link:
            Keyword.objects.bulk_create(keywords_to_link)

    # SOLO PARA LO SUGERIDO (SIN SINONIMOS)
    def populate_strategy_from_structured_data(self, strategy_id: int, keyword_data: list[dict]):
        strategy = SearchStrategy.objects.select_related('research_question').get(id=strategy_id)
        self._link_project_keywords_to_strategy(strategy, keyword_data)

    # Método para sincronizar UNICAMENTE términos sugeridos con una estrategia
    def sync_suggested_terms_with_strategy(self, research_question_id: int, suggested_terms: list[str]) -> SearchStrategy:
        # 1. Obtener o crear la estrategia
        strategy = self._get_or_create_strategy(research_question_id)
        # 2. Convertir la lista de strings al formato de datos estructurados
        keyword_data = [{'term': term, 'synonyms': ''} for term in suggested_terms]
        # 3. Llamar al método central para hacer el enlace
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