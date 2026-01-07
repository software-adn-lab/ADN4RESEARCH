from abc import ABC, abstractmethod
from typing import List
from apps.design.api.dtos import DesignScheduleDTO
from apps.design.api.dtos import (QuestionDTO, CriterionDTO)

class IDesignProtocol(ABC):
    """
    Interface que expone los artefactos del protocolo de diseño consolidado.

    Responsabilidades:
    - Proveer acceso a preguntas de investigación aprobadas
    - Proveer acceso a criterios de elegibilidad (inclusion y exclusion) aprobados
    """

    @abstractmethod
    def get_protocol_questions(self, project_id: int) -> List[QuestionDTO]:
        """
        Obtener las preguntas de investigación aprobadas del protocolo.

        Args:
            project_id: ID del proyecto

        Returns:
            Lista de dicts con id y question
        """
        pass

    @abstractmethod
    def get_inclusion_criteria(self, project_id: int) -> List[CriterionDTO]:
        """
        Obtener los criterios de inclusión aprobados.

        Args:
            project_id: ID del proyecto

        Returns:
            Lista de dicts con id y description
        """
        pass

    @abstractmethod
    def get_exclusion_criteria(self, project_id: int) -> List[CriterionDTO]:
        """
        Obtener los criterios de exclusión aprobados.

        Args:
            project_id: ID del proyecto

        Returns:
            Lista de dicts con id y description
        """
        pass

class IDesignManagement(ABC):
    """
    Contrato administrativo para la orquestación de la fase de diseño.
    """

    @abstractmethod
    def initialize_design_schedule(self, project_id: int, schedule: List[DesignScheduleDTO]) -> int:
        """
        Inicializa la planificación de etapas para un proyecto dado.
        """
        pass

    @abstractmethod
    def get_design_stages_info(self) -> List[dict]:
        """
        Retorna información sobre las etapas de diseño disponibles (keys y labels).
        """
        pass
