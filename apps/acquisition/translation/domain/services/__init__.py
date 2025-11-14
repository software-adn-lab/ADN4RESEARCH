"""
Translation services - Traductores de estrategias de búsqueda.

Contiene los traductores específicos para cada base de datos académica.
"""

from .translation_result import TranslationResult
from .istrategy_translator import IStrategyTranslator
from .scopus_translator import ScopusTranslator
from .ieee_translator import IeeeTranslator

__all__ = [
    "TranslationResult",
    "IStrategyTranslator",
    "ScopusTranslator",
    "IeeeTranslator",
]
