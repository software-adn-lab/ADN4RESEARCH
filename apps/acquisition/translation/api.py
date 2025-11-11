"""
Public API for the translation component.

This module provides the façade for external components to interact
with the translation functionality.
"""

from .application.translation_service import TranslationService
from .domain.models import NormalizedStrategy
from .domain.services.translation_result import TranslationResult
from .domain.services.istrategy_translator import IStrategyTranslator
from .domain.services.scopus_translator import ScopusTranslator
from .domain.services.ieee_translator import IeeeTranslator

__all__ = [
    "TranslationService",
    "NormalizedStrategy",
    "TranslationResult",
    "IStrategyTranslator",
    "ScopusTranslator",
    "IeeeTranslator",
]
