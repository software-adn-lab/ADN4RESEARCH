from apps.design.search_strategy.models.keyword import Keyword, ProjectKeyword
from apps.design.search_strategy.models.search_strategy import SearchStrategy


class SearchStrategyService:
    def generate_and_save_search_string(self, strategy: SearchStrategy) -> SearchStrategy:
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
    
    def populate_strategy_keywords(self, strategy: SearchStrategy, keyword_data: list[dict]):
        project = strategy.research_question.project
        keywords_to_link = []
        for item in keyword_data:
            project_keyword, created = ProjectKeyword.objects.get_or_create(
                project=project,
                term=item['term'],
                defaults={'synonyms': item.get('synonyms', '')}
            )
            keywords_to_link.append(
                Keyword(strategy=strategy, project_keyword=project_keyword)
            )
        if keywords_to_link:
            Keyword.objects.bulk_create(keywords_to_link)
            
    def create_project_keyword(self, project, term: str, synonyms: str) -> ProjectKeyword:
        project_keyword = ProjectKeyword.objects.create(
            project=project,
            term=term,
            synonyms=synonyms
        )
        return project_keyword
    
    def get_strategy_for_question(self, question):
        return SearchStrategy.objects.filter(research_question=question).first()