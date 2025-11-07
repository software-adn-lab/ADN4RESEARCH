"""
Interfaz para traductores de estrategias de búsqueda.
"""

from abc import ABC, abstractmethod
from apps.acquisition.domain.models import NormalizedStrategy
from .translation_result import TranslationResult


class IStrategyTranslator(ABC):
    """
    Interfaz para traductores de estrategias a diferentes bases de datos.

    Cada base de datos académica (Scopus, IEEE Xplore, WoS, etc.) tiene
    su propio dialecto de búsqueda. Los traductores implementan esta interfaz
    para convertir una estrategia normalizada al dialecto específico.

    Responsabilidades de un traductor:
    1. Construir la query en el dialecto del target
    2. Generar warnings si el target tiene limitaciones
    3. Registrar steps y rules para trazabilidad
    4. Retornar metadata relevante
    """

    @abstractmethod
    def translate(self, strategy: NormalizedStrategy) -> TranslationResult:
        """
        Traduce una estrategia normalizada al dialecto del target.

        Args:
            strategy: Estrategia normalizada e inmutable

        Returns:
            TranslationResult con query, warnings, steps, rules, metadata

        Raises:
            DomainValidationError: Si la estrategia tiene problemas de validación
        """
        pass
