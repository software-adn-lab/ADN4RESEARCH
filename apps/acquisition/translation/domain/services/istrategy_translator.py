"""
Interfaz para traductores de estrategias de búsqueda.
"""

from abc import ABC, abstractmethod
from apps.acquisition.translation.domain.models import NormalizedStrategy
from .translation_result import TranslationResult


class IStrategyTranslator(ABC):
    """Interfaz para traductores de estrategias a diferentes bases de datos."""

    @abstractmethod
    def translate(self, strategy: NormalizedStrategy) -> TranslationResult:
        """
        Traduce una estrategia normalizada al dialecto del target.

        Args:
            strategy: Estrategia normalizada e inmutable

        Returns:
            TranslationResult con query, warnings, steps, rules, metadata
        """
        pass
