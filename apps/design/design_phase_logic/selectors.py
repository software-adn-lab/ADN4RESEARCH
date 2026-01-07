from apps.design.design_phase_logic.models.design_phase import DesignPhase, DesignStagePlan
from apps.design.design_phase_logic.dtos import DesignTimelineStageDTO


class DesignPhaseSelector:
    """
    Handles read-only queries for Design Phase.
    Separates Query responsibility from the Service (Command).
    """

    @staticmethod
    def get_current_stage_plan(project_id: int) -> DesignStagePlan | None:
        """
        Retorna el plan (fechas) de la etapa actual.
        """
        try:
            phase = DesignPhase.objects.get(pk=project_id)
            return DesignStagePlan.objects.filter(phase=phase, stage=phase.current_stage).first()
        except DesignPhase.DoesNotExist:
            return None

    @staticmethod
    def get_design_timeline_context(project_id: int) -> list[DesignTimelineStageDTO]:
        """
        Retorna el estado de la línea de tiempo para la UI.
        Calcula estados 'upcoming', 'current', 'completed'.
        """
        try:
            phase = DesignPhase.objects.get(pk=project_id)
        except DesignPhase.DoesNotExist:
            return []

        current_stage = phase.current_stage
        design_flow = DesignPhase.DESIGN_FLOW
        timeline_stages = []
        is_past = True

        for stage_key in design_flow:
            status = 'upcoming'
            if stage_key == current_stage:
                is_past = False
                status = 'current'
            elif stage_key == DesignPhase.DesignStage.FINISHED:
                status = 'finished'
            elif is_past:
                status = 'completed'

            # Recuperamos la etiqueta legible del enum
            label = DesignPhase.DesignStage(stage_key).label

            timeline_stages.append(DesignTimelineStageDTO(
                key=stage_key,
                label=label,
                status=status
            ))
        return timeline_stages
