"""
ConsolidationResult - Resultado del proceso de consolidación.

DTO que agrupa los estudios procesados y un resumen estadístico.
Es el valor de retorno del ConsolidationService.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any

from apps.acquisition.shared.domain.entities.study import Study


@dataclass
class ConsolidationResult:
    """
    Resultado del proceso de consolidación de metadatos.

    Attributes:
        studies: Lista de estudios con metadatos consolidados
        summary: Resumen estadístico del proceso
            {
                "total_processed": int,
                "successful": int,
                "failed": int,
                "campos_completados": int,
                "campos_normalizados": int
            }
    """
    studies: List[Study]
    summary: Dict[str, Any] = field(default_factory=dict)

    def get_studies_by_status(self, status: str) -> List[Study]:
        """
        Filtra estudios por estado de consolidación.

        Args:
            status: Estado a filtrar (completo/parcial/fallido)

        Returns:
            Lista de estudios con ese estado
        """
        return [s for s in self.studies if s.consolidation_status == status]

    @property
    def successful_studies(self) -> List[Study]:
        """Estudios que se consolidaron exitosamente (completo o parcial)."""
        return [s for s in self.studies
                if s.consolidation_status in ("completo", "parcial")]

    @property
    def failed_studies(self) -> List[Study]:
        """Estudios que fallaron la consolidación."""
        return [s for s in self.studies
                if s.consolidation_status == "fallido"]
