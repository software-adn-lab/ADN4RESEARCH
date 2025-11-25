from typing import List, Optional
from ...domain.repositories.i_design_repository import IDesignRepository
from ...domain.dtos.design_dtos import ResearchQuestionDTO

try:
    from apps.design.services import DesignService  # ✅ Usa servicio
except ImportError:
    DesignService = None


class DesignServiceAdapter(IDesignRepository):

    def __init__(self):
        self.service = DesignService() if DesignService else None

    def get_question_by_id(self, question_id: int) -> Optional[ResearchQuestionDTO]:
        if not self.service:
            return None

        data = self.service.get_question_details(question_id)
        if not data:
            return None

        return ResearchQuestionDTO(
            id=data['id'],
            text=data['text'],
            project_id=data['project_id']
        )

    def get_questions_by_project(self, project_id: int) -> List[ResearchQuestionDTO]:
        if not self.service:
            return []

        questions = self.service.get_questions_by_project(project_id)
        return [
            ResearchQuestionDTO(
                id=q['id'],
                text=q['text'],
                project_id=q['project_id']
            )
            for q in questions
        ]

    def question_exists(self, question_id: int) -> bool:
        if not self.service:
            return False
        return self.service.question_exists(question_id)