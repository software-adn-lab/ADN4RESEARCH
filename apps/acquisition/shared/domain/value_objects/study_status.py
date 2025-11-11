"""
StudyStatus Value Object - Estados del ciclo de vida de un Study.
"""

from enum import Enum
from typing import Set


class StudyStatus(str, Enum):
    """
    Estados posibles de un Study en el workflow de adquisición.

    El Study evoluciona a través de estos estados:
        DISCOVERED → ENRICHED → DOWNLOADED

    Estados:
        DISCOVERED: Estudio descubierto en búsqueda (tiene título, link, source)
        ENRICHED: Metadatos completos obtenidos (authors, abstract, year, etc.)
        DOWNLOADED: Texto completo (PDF) descargado y validado
        FAILED: El estudio no pudo ser procesado (error irrecuperable)
    """

    DISCOVERED = "discovered"
    ENRICHED = "enriched"
    DOWNLOADED = "downloaded"
    FAILED = "failed"

    def can_transition_to(self, target_status: "StudyStatus") -> bool:
        """
        Validar si es posible transicionar al estado objetivo.

        Reglas de transición:
            - DISCOVERED → ENRICHED, FAILED
            - ENRICHED → DOWNLOADED, FAILED
            - DOWNLOADED → (final, no puede transicionar)
            - FAILED → (final, no puede transicionar)

        Args:
            target_status: Estado objetivo

        Returns:
            True si la transición es válida, False en caso contrario
        """
        valid_transitions: dict[StudyStatus, Set[StudyStatus]] = {
            StudyStatus.DISCOVERED: {StudyStatus.ENRICHED, StudyStatus.FAILED},
            StudyStatus.ENRICHED: {StudyStatus.DOWNLOADED, StudyStatus.FAILED},
            StudyStatus.DOWNLOADED: set(),  # Estado final
            StudyStatus.FAILED: set(),  # Estado final
        }

        return target_status in valid_transitions[self]

    def is_final(self) -> bool:
        """
        Verificar si el estado es final (no puede transicionar).

        Returns:
            True si el estado es DOWNLOADED o FAILED
        """
        return self in {StudyStatus.DOWNLOADED, StudyStatus.FAILED}

    def __str__(self) -> str:
        """Representación en string del estado."""
        return self.value
