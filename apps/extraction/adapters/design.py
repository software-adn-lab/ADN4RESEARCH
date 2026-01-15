from typing import List
from dataclasses import dataclass
from apps.design.api.providers import DesignProtocolProvider 

@dataclass(frozen=True)
class ResearchQuestionDTO:
    id: int
    text: str
    variable: str

class DesignAdapter:
    """
    ACL para el contexto de Design.
    Traduce los modelos de Design a DTOs que Extraction entiende.
    """
    def __init__(self):
        self._provider = DesignProtocolProvider()

    def get_protocol_questions(self, project_id: int) -> List[ResearchQuestionDTO]:
        """
        Obtiene las preguntas de investigación del protocolo.
        Retorna List[ResearchQuestionDTO] para mantener desacoplamiento.
        """
        raw_questions = self._provider.get_protocol_questions(project_id)
        
        return [
            ResearchQuestionDTO(
                id=q['id'],
                text=q['question'],
                variable=q.get('variable', '')
            )
            for q in raw_questions
        ]

    def get_research_question_by_id(self, rq_id: int):
        """
        Obtiene una instancia de ResearchQuestion (modelo Django) por su ID.
        Este método es para obtener instancias reales cuando es necesario
        para relaciones ForeignKey en el modelo.
        """
        from apps.design.research_question.models.research_question import ResearchQuestion
        return ResearchQuestion.objects.get(id=rq_id)