"""
DiscoveryResult entity for the discovery domain.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from apps.acquisition.shared.domain.entities.study import Study


@dataclass
class DiscoveryResult:
    """Represents the result of a discovery operation."""
    studies: List[Study] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    # Properties para compatibilidad con el Orchestrator
    @property
    def total_unique_studies(self) -> int:
        """Total de estudios únicos (deduplicados)."""
        return self.summary.get("total_unicos", len(self.studies))

    @property
    def total_raw_studies(self) -> int:
        """Total de estudios brutos (antes de deduplicación)."""
        return self.summary.get("total_bruto", len(self.studies))

    @property
    def total_por_fuente(self) -> Dict[str, int]:
        """Cantidad de estudios retornados por fuente (limitados por max_results)."""
        return self.summary.get("total_por_fuente", {})

    @property
    def total_available_by_source(self) -> Dict[str, Optional[int]]:
        """Total de estudios disponibles en la API por fuente.
        
        Este es el número REAL de resultados que la API reporta, no el limitado.
        Útil para mostrar "25 de 152,340" en el UI.
        
        Returns:
            Dict mapping source name to total available (None if not provided by API)
        """
        return self.summary.get("total_available_by_source", {})

    @property
    def studies_by_source(self) -> Dict[str, List[Study]]:
        """Estudios agrupados por fuente (para trazabilidad)."""
        return self.summary.get("studies_by_source", {})

    @property
    def not_executed_sources(self) -> Dict[str, str]:
        """Fuentes que no se ejecutaron con su razón."""
        return self.summary.get("no_ejecutadas", {})

    @property
    def errors(self) -> Dict[str, str]:
        """Errores por fuente (alias de not_executed_sources)."""
        return self.not_executed_sources

    @property
    def results_by_source(self) -> Dict[str, List[Study]]:
        """Alias para studies_by_source (compatibilidad con Orchestrator)."""
        return self.studies_by_source

    def to_dict(self) -> Dict[str, Any]:
        """Convert discovery result to a dictionary."""
        return {
            "studies": [study.to_dict() for study in self.studies],
            "summary": self.summary
        }