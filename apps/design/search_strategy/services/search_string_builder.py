class SearchStringBuilder:
    def build_from_json(self, data: dict) -> str:
        """
        Builds a boolean search string from the JSON definition.
        """
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
