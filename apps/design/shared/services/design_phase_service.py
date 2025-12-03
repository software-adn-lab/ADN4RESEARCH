from apps.design.shared.models.design_phase import DesignPhase

class DesignPhaseService:
    
    def get_current_stage_deadline(self, project_id: int):
        try:
            phase = DesignPhase.objects.get(pk=project_id)
            return phase.end_date
        except DesignPhase.DoesNotExist:
            return None

    def get_design_timeline_context(self, project_id: int):
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
            label = DesignPhase.DesignStage(stage_key).label 

            timeline_stages.append({
                'key': stage_key,
                'label': label,
                'status': status
            })
        return timeline_stages