from typing import List, Optional
from django.contrib.auth.models import User
from apps.design.research_question.models.research_question import ResearchQuestion
from apps.design.research_question.dtos import ResearchQuestionDTO
from apps.design.access_control import DesignAccessPolicy


class ResearchQuestionSelector:
    """
    Handles all read-only queries for Research Questions.
    Returns DTOs to decouple the View from the Model.
    """

    @staticmethod
    def get_question_dto(question: ResearchQuestion, user: User) -> ResearchQuestionDTO:
        """
        Maps a model instance to a DTO.
        """
        return ResearchQuestionDTO(
            id=question.id,
            question=question.question,
            motivation=question.motivation,
            status=question.status,
            status_label=question.get_status_display(),
            framework_fields=question.framework_fields,
            researcher_name=question.researcher.get_full_name() or question.researcher.username if question.researcher else "Unknown",
            is_editable=DesignAccessPolicy.can_edit_question(user, question),
            created_at=question.created_at,
            modified_at=question.modified_at,
            justification=question.justification,
            reviewed_by_name=question.reviewed_by.get_full_name() if question.reviewed_by else None,
            reviewed_at=question.reviewed_at
        )

    @staticmethod
    def get_by_id(question_id: int, user: User) -> Optional[ResearchQuestionDTO]:
        try:
            question = ResearchQuestion.objects.select_related('researcher', 'design_phase__project').get(pk=question_id)
            # Check visibility permissions if needed, for now assuming if you are in the project you can see it
            return ResearchQuestionSelector.get_question_dto(question, user)
        except ResearchQuestion.DoesNotExist:
            return None

    @staticmethod
    def get_list_for_workspace(project_id: int, user: User, status_filter: str = None) -> List[ResearchQuestionDTO]:
        qs = ResearchQuestion.objects.filter(design_phase_id=project_id).select_related('researcher', 'design_phase__project')

        if status_filter:
            qs = qs.filter(status=status_filter)

        qs = qs.order_by('-modified_at')

        return [ResearchQuestionSelector.get_question_dto(q, user) for q in qs]

    @staticmethod
    def get_list_for_discussion(project_id: int, user: User, status_filter: str = None) -> List[ResearchQuestionDTO]:
        qs = ResearchQuestion.objects.filter(design_phase_id=project_id).filter(status__in=ResearchQuestion.DISCUSSION_PHASE_STATUSES).select_related('researcher', 'design_phase__project')

        if status_filter:
            qs = qs.filter(status=status_filter)

        qs = qs.order_by('-modified_at')

        return [ResearchQuestionSelector.get_question_dto(q, user) for q in qs]
