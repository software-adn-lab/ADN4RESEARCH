import hashlib
import json
from typing import List, Optional
from django.core.cache import cache
from apps.acquisition.facade import get_acquisition_facade
from apps.acquisition.shared.domain.constants import normalize_source_names
from apps.design.search_strategy.services.nlp.translation_service import TranslationService
from apps.design.search_strategy.models.search_strategy import SearchStrategy


class SearchPreviewService:
    def __init__(self):
        self.translation_service = TranslationService()
        self.acquisition_facade = get_acquisition_facade()

    def get_search_results_dto(
        self,
        strategy: SearchStrategy,
        selected_sources: Optional[List[str]] = None
    ):
        """
        Retrieves search results preview for a given strategy.
        Handles caching and translation.
        
        Args:
            strategy: SearchStrategy model instance
            selected_sources: Lista de fuentes a consultar (opcional).
                             Acepta nombres UI ("IEEE") o canónicos ("IEEE Xplore").
                             Si es None, consulta todas las fuentes disponibles.
        
        Returns:
            PreviewSearchResult with studies and metadata
        """
        strategy_hash = hashlib.md5(
            json.dumps(strategy.json_definition, sort_keys=True).encode()
        ).hexdigest()
        
        # Normalizar fuentes antes de crear cache key para evitar duplicados
        # "IEEE" y "IEEE Xplore" deben generar la misma clave
        normalized_sources = normalize_source_names(selected_sources)
        sources_key = ",".join(sorted(normalized_sources or ["all"]))
        cache_key = f"search_preview:{strategy.id}:{strategy_hash}:{sources_key}"
        
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        try:
            json_definition_translated = self.translation_service.translate_json_definition(
                strategy.json_definition
            )
            results_dto = self.acquisition_facade.preview_search(
                json_definition_translated,
                selected_sources=selected_sources,
            )
            cache.set(cache_key, results_dto, timeout=86400)
            return results_dto
        except Exception as e:
            raise RuntimeError(f"Error fetching search results: {e}")

    def translate_and_preview(
        self,
        visual_data: dict,
        selected_sources: Optional[List[str]] = None
    ):
        """
        Translates the visual data and fetches a preview.
        Useful for real-time feedback during strategy building.
        
        Args:
            visual_data: Strategy definition as dict
            selected_sources: Lista de fuentes a consultar (opcional)
        
        Returns:
            int: Total number of studies found
        """
        try:
            translated_json = self.translation_service.translate_json_definition(visual_data)
            preview_result = self.acquisition_facade.preview_search(
                translated_json,
                selected_sources=selected_sources,
            )
            return getattr(preview_result, 'total_found', 0)
        except Exception as e:
            # Log error but don't crash the flow, return 0 results
            print(f"Error fetching search preview: {e}")
            return 0
