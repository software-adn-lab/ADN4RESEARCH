from abc import ABC, abstractmethod
from typing import List, TypedDict


class QuestionDTO(TypedDict):
    """Datos mínimos de una pregunta de investigación."""
    id: int
    question: str


class CriterionDTO(TypedDict):
    """Datos mínimos de un criterio de elegibilidad."""
    id: int
    description: str


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
