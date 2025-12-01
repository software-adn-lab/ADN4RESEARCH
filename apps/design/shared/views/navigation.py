from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from apps.design.shared.models.design_phase import DesignPhase

@login_required
def design_stages_router(request, project_id):
    target_stage = request.GET.get('target_stage')
    stage_map = {
        DesignPhase.DesignStage.RQ_CREATION.value: 'design:rq_workspace',
        DesignPhase.DesignStage.RQ_DISCUSSION.value: 'design:question_discussion_panel',
        DesignPhase.DesignStage.CRITERIA_DEFINITION.value: 'design:eligibility_criteria_panel',
    }

    url_name = stage_map.get(target_stage, 'design:rq_workspace')
    
    return redirect(url_name, project_id=project_id)