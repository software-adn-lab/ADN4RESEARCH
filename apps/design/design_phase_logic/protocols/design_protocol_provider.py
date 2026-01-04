from typing import List
from apps.design.design_phase_logic.protocols.design_protocol import (
    IDesignProtocol,
    QuestionDTO,
    CriterionDTO,
)
from apps.design.research_question.models.research_question import ResearchQuestion
from apps.design.eligibility_criteria.models.eligibility_criteria import EligibilityCriterion


class DesignProtocolProvider(IDesignProtocol):
    """
    Implementación concreta de IDesignProtocol.

    Retorna solo id y texto de los artefactos aprobados.
    """

    def get_protocol_questions(self, project_id: int) -> List[QuestionDTO]:
        """
        Obtener id y texto de las preguntas aprobadas.
        """
        questions = (
            ResearchQuestion.objects
            .by_project(project_id)
            .by_status(ResearchQuestion.Status.APPROVED)
            .values('id', 'question')
            .order_by('created_at')
        )
        protocol_questions = [{'id': q['id'], 'question': q['question']} for q in questions]
        return protocol_questions

    def get_inclusion_criteria(self, project_id: int) -> List[CriterionDTO]:
        """
        Obtener id y descripción de los criterios de inclusión aprobados.
        """
        criteria = (
            EligibilityCriterion.objects
            .by_project(project_id)
            .by_type(EligibilityCriterion.CriterionType.INCLUSION)
            .filter(status=EligibilityCriterion.CriterionStatus.APPROVED)
            .values('id', 'description')
            .order_by('created_at')
        )
        protocol_inclusion_criteria = [{'id': c['id'], 'description': c['description']} for c in criteria]
        return protocol_inclusion_criteria

    def get_exclusion_criteria(self, project_id: int) -> List[CriterionDTO]:
        """
        Obtener id y descripción de los criterios de exclusión aprobados.
        """
        criteria = (
            EligibilityCriterion.objects
            .by_project(project_id)
            .by_type(EligibilityCriterion.CriterionType.EXCLUSION)
            .filter(status=EligibilityCriterion.CriterionStatus.APPROVED)
            .values('id', 'description')
            .order_by('created_at')
        )
        protocol_exclusion_criteria = [{'id': c['id'], 'description': c['description']} for c in criteria]
        return protocol_exclusion_criteria
