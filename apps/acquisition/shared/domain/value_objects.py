"""
Value Objects para el dominio de Acquisition.

Los Value Objects son objetos inmutables que encapsulan datos con validación
y comportamiento, identificándose por su valor y no por identidad.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from .constants import TranslationStatus, TRANSLATION_STATUS_READY, TRANSLATION_STATUS_NOT_SUPPORTED


@dataclass(frozen=True)
class TranslationStatusInfo:
    """
    Representa el estado de una traducción para una fuente específica.

    Contrato usado por DiscoveryService para determinar qué fuentes consultar.

    Attributes:
        status: Estado de la traducción ("ready" | "not_supported")
        query: Query traducida (presente si status="ready", None si not_supported)

    Invariantes:
        - Si status="ready", query debe estar presente y no vacía
        - Si status="not_supported", query debe ser None

    Ejemplos:
        >>> # Traducción exitosa
        >>> TranslationStatusInfo(status="ready", query="TITLE-ABS-KEY(...)")

        >>> # Traducción no soportada
        >>> TranslationStatusInfo(status="not_supported", query=None)
    """

    status: TranslationStatus
    query: Optional[str]

    def __post_init__(self):
        """Validar invariantes del contrato."""
        if self.status == TRANSLATION_STATUS_READY:
            if not self.query or not self.query.strip():
                raise ValueError(
                    f"Cuando status='{TRANSLATION_STATUS_READY}', "
                    f"query debe estar presente y no vacía"
                )
        elif self.status == TRANSLATION_STATUS_NOT_SUPPORTED:
            if self.query is not None:
                raise ValueError(
                    f"Cuando status='{TRANSLATION_STATUS_NOT_SUPPORTED}', "
                    f"query debe ser None"
                )
        else:
            raise ValueError(
                f"status debe ser '{TRANSLATION_STATUS_READY}' o "
                f"'{TRANSLATION_STATUS_NOT_SUPPORTED}', no '{self.status}'"
            )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TranslationStatusInfo':
        """
        Crear desde diccionario.

        Args:
            data: {"status": str, "query": Optional[str]}

        Returns:
            TranslationStatusInfo validado

        Raises:
            ValueError: Si el contrato no se cumple
        """
        if "status" not in data:
            raise ValueError("El campo 'status' es obligatorio")

        return cls(
            status=data["status"],
            query=data.get("query")
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serializar a diccionario."""
        return {
            "status": self.status,
            "query": self.query
        }

    def is_ready(self) -> bool:
        """Verificar si la traducción está lista para consultar."""
        return self.status == TRANSLATION_STATUS_READY
