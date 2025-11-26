from abc import ABC, abstractmethod
from typing import List, Optional
from ..dtos.design_dtos import ResearchQuestionDTO

class IDesignRepository(ABC):
    """
    Puerto para comunicarse con el Bounded Context de 'Design'.
    """

    @abstractmethod
    def get_question_by_id(self, question_id: int) -> Optional[ResearchQuestionDTO]:
        """Obtiene el detalle de una pregunta específica."""
        pass

    @abstractmethod
    def get_questions_by_project(self, project_id: int) -> List[ResearchQuestionDTO]:
        """Obtiene todas las preguntas asociadas a un proyecto."""
        pass

    @abstractmethod
    def question_exists(self, question_id: int) -> bool:
        """Verificación rápida de existencia."""
        pass