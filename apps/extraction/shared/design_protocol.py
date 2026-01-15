from typing import List

from apps.design.api.providers import DesignProtocolProvider
from apps.design.api.dtos import QuestionDTO


class DesignProtocolAdapter:
    """
    Adaptador para consumir el protocolo aprobado desde Design.
    """

    def __init__(self) -> None:
        self._provider = DesignProtocolProvider()

    def get_approved_questions(self, project_id: int) -> List[QuestionDTO]:
        return self._provider.get_protocol_questions(project_id)

    def get_approved_question_ids(self, project_id: int) -> List[int]:
        questions = self.get_approved_questions(project_id)
        return [q["id"] for q in questions]
