
from typing import List

from apps.design.search_strategy.models.keyword import Keyword
from apps.design.search_strategy.models.search_strategy import SearchStrategy


class SearchStrategyService:
    def generate_and_save_search_string(self, strategy: SearchStrategy) -> SearchStrategy:
        keywords = strategy.keywords.all()
        
        if not keywords:
            strategy.final_search_string = ""
            strategy.save()
            return strategy
        or_groups = []
        for kw in keywords:
            terms = [f'"{kw.term}"']
            if kw.synonyms and kw.synonyms.strip():
                # Asumimos que están guardados como "syn1, syn2, syn3"
                synonyms_list = [s.strip() for s in kw.synonyms.split(',')]
                for s in synonyms_list:
                    if s:
                        terms.append(f'"{s}"')
            group_string = ' OR '.join(terms)
            or_groups.append(f"({group_string})")
        final_string = " AND ".join(or_groups)
        final_string = f"({final_string})"
        strategy.final_search_string = final_string
        strategy.save()
        
        return strategy
    
    def populate_strategy_keywords(self, strategy: SearchStrategy, keyword_data: list[dict]):
        keywords_to_create = [
            Keyword(
                strategy=strategy,
                term=item['term'],
                synonyms=item['synonyms']
            )
            for item in keyword_data
        ]
        if keywords_to_create:
            Keyword.objects.bulk_create(keywords_to_create)