from abc import ABC, abstractmethod
from typing import Optional
from ..entities.extraction_phase import ExtractionPhase


class IExtractionPhaseRepository(ABC):
    """Puerto para gestionar la configuración de la fase de extracción"""

    @abstractmethod
    def get_by_project_id(self, project_id: int) -> Optional[ExtractionPhase]:
        """Obtiene la fase de extracción de un proyecto"""
        pass

    @abstractmethod
    def save(self, phase: ExtractionPhase) -> ExtractionPhase:
        """Persiste la configuración de la fase"""
        pass

    @abstractmethod
    def get_active_phases_to_close(self) -> list[ExtractionPhase]:
        """
        Obtiene fases activas con auto_close que ya pasaron end_date.
        Útil para un job periódico.
        """
        pass