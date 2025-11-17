"""
DOI (Digital Object Identifier) Value Object.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DOI:
    """
    Representa un DOI (Digital Object Identifier) válido.

    El DOI es un identificador único y persistente para recursos digitales.
    Formato típico: 10.xxxx/yyyyy

    Attributes:
        value: El valor del DOI (ej: "10.1109/TSE.2020.12345")

    Invariantes:
        - El DOI debe seguir el formato estándar (10.xxxx/...)
        - No puede ser vacío

    Ejemplos:
        >>> doi = DOI("10.1109/TSE.2020.12345")
        >>> doi.value
        '10.1109/TSE.2020.12345'

        >>> doi.url()
        'https://doi.org/10.1109/TSE.2020.12345'
    """

    value: str

    # Patrón regex para validar formato DOI: 10.xxxx/yyyyy
    DOI_PATTERN = re.compile(r"^10\.\d{4,9}/[^\s]+$")

    def __post_init__(self):
        """Validar el formato del DOI."""
        if not self.value or not self.value.strip():
            raise ValueError("DOI no puede estar vacío")

        # Normalizar: remover espacios
        normalized = self.value.strip()

        # Validar formato
        if not self.DOI_PATTERN.match(normalized):
            raise ValueError(
                f"DOI inválido: '{self.value}'. "
                f"Debe seguir el formato: 10.xxxx/yyyyy"
            )

        # Usar object.__setattr__ porque el dataclass es frozen
        object.__setattr__(self, "value", normalized)

    @classmethod
    def from_optional_string(cls, value: Optional[str]) -> Optional["DOI"]:
        """
        Crear un DOI desde un string opcional.

        Args:
            value: String con el DOI o None

        Returns:
            DOI si el string es válido, None si es None o vacío

        Raises:
            ValueError: Si el formato del DOI es inválido
        """
        if not value or not value.strip():
            return None
        return cls(value)

    def url(self) -> str:
        """
        Obtener la URL completa del DOI.

        Returns:
            URL en formato https://doi.org/{doi}
        """
        return f"https://doi.org/{self.value}"

    def __str__(self) -> str:
        """Representación en string del DOI."""
        return self.value
