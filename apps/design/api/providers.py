from typing import List
from apps.design.api.contracts import (
    IDesignManagement,
    IDesignProtocol,
)
from apps.design.api.dtos import (DesignScheduleDTO, QuestionDTO, CriterionDTO)
from apps.design.design_phase_logic.services.design_phase_service import DesignPhaseService
from apps.design.research_question.models.research_question import ResearchQuestion
from apps.design.eligibility_criteria.models.eligibility_criteria import EligibilityCriterion
from apps.design.design_phase_logic.models.design_phase import DesignPhase

class DesignProtocolProvider(IDesignProtocol):
    """
    Clase que implementa a la interfaz IDesignProtocol.

    Retorna solo id y texto de los artefactos aprobados segun lo conversado con seleccion y extraccion.
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

class DesignManagementProvider(IDesignManagement):
    """
    Implementa IDesignManagement.
    Encargado de recibir configuraciones administrativas (Fechas, Setup) desde el Módulo de Proyecto.
    """

    def __init__(self):
        self._service = DesignPhaseService()

    def initialize_design_schedule(self, project_id: int, schedule: List[DesignScheduleDTO]) -> int:
        schedule_data = [
            {
                'stage': item.stage,
                'start': item.start_date,
                'end': item.end_date
            }
            for item in schedule
        ]

        return self._service.initialize_design_schedule(project_id, schedule_data)

    def get_design_stages_info(self) -> List[dict]:
        
        stages_info = []
        for stage_key in DesignPhase.DESIGN_FLOW:
            label = DesignPhase.DesignStage(stage_key).label
            stages_info.append({
                'key': stage_key,
                'label': label
            })
        return stages_info
