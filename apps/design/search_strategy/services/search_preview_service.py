import hashlib
import json
from django.core.cache import cache
from apps.acquisition.facade import get_acquisition_facade
from apps.design.search_strategy.services.nlp.translation_service import TranslationService
from apps.design.search_strategy.models.search_strategy import SearchStrategy


class SearchPreviewService:
    def __init__(self):
        self.translation_service = TranslationService()
        self.acquisition_facade = get_acquisition_facade()

    def get_search_results_dto(self, strategy: SearchStrategy):
        """
        Retrieves search results preview for a given strategy.
        Handles caching and translation.
        """
        strategy_hash = hashlib.md5(json.dumps(strategy.json_definition, sort_keys=True).encode()).hexdigest()
        cache_key = f"search_preview:{strategy.id}:{strategy_hash}"
        cached_result = cache.get(cache_key)

        if cached_result:
            return cached_result

        try:
            json_definition_translated = self.translation_service.translate_json_definition(strategy.json_definition)
            results_dto = self.acquisition_facade.preview_search(json_definition_translated)
            cache.set(cache_key, results_dto, timeout=86400)
            return results_dto
        except Exception as e:
            raise RuntimeError(f"Error fetching search results: {e}")

    def translate_and_preview(self, visual_data: dict):
        """
        Translates the visual data and fetches a preview.
        Useful for real-time feedback during strategy building.
        """
        try:
            translated_json = self.translation_service.translate_json_definition(visual_data)
            preview_result = self.acquisition_facade.preview_search(translated_json)
            return getattr(preview_result, 'total_found', 0)
        except Exception as e:
            # Log error but don't crash the flow, return 0 results
            print(f"Error fetching search preview: {e}")
            return 0
