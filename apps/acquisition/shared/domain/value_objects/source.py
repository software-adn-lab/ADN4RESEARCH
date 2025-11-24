"""
Source Value Object - Representa una fuente académica.
"""

from dataclasses import dataclass
from apps.acquisition.shared.domain.constants import SUPPORTED_SOURCES


@dataclass(frozen=True)
class Source:
    """
    Representa una fuente académica válida.

    Las fuentes académicas son las bases de datos de donde se obtienen los estudios
    (ej: Scopus, IEEE Xplore, arXiv, etc.)

    Attributes:
        name: Nombre de la fuente académica

    Invariantes:
        - El nombre debe estar en la lista de fuentes soportadas (SUPPORTED_SOURCES)
        - No puede ser vacío

    Ejemplos:
        >>> source = Source("Scopus")
        >>> source.name
        'Scopus'

        >>> source.is_supported()
        True
    """

    name: str

    def __post_init__(self):
        """Validar que la fuente sea válida."""
        if not self.name or not self.name.strip():
            raise ValueError("El nombre de la fuente no puede estar vacío")

        # Normalizar: remover espacios
        normalized = self.name.strip()

        # Validar que esté en la lista de fuentes soportadas
        if normalized not in SUPPORTED_SOURCES:
            raise ValueError(
                f"Fuente no soportada: '{self.name}'. "
                f"Fuentes válidas: {', '.join(SUPPORTED_SOURCES)}"
            )

        # Usar object.__setattr__ porque el dataclass es frozen
        object.__setattr__(self, "name", normalized)

    def is_supported(self) -> bool:
        """
        Verificar si la fuente está soportada.

        Returns:
            True (siempre, porque la validación se hace en __post_init__)
        """
        return True

    def __str__(self) -> str:
        """Representación en string de la fuente."""
        return self.name

    def __eq__(self, other) -> bool:
        """Comparar fuentes por nombre."""
        if not isinstance(other, Source):
            return False
        return self.name == other.name

    def __hash__(self) -> int:
        """Hash basado en el nombre."""
        return hash(self.name)
