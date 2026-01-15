from django.shortcuts import redirect
from apps.design.design_phase_logic.models.design_phase import DesignPhase
# REFACTORED: Import decorator from shared module
from apps.shared.decorators import project_member_required


@project_member_required
def design_stages_router(request, project_id, project_dto):
    """
    Router that redirects to the appropriate stage view based on query param or current stage.

    CHANGED: project parameter is now project_dto (dict from IProjectManagement)
    """
    target_stage = request.GET.get('target_stage')
    stage_map = {
        DesignPhase.DesignStage.RQ_CREATION.value: 'research-questions/',
        DesignPhase.DesignStage.RQ_DISCUSSION.value: 'discussion/',
        DesignPhase.DesignStage.CRITERIA_DEFINITION.value: 'eligibility-criteria/',
        DesignPhase.DesignStage.SEARCH_STRATEGY.value: 'strategies/',
        DesignPhase.DesignStage.FINISHED.value: 'dashboard/',
    }

    relative_path = stage_map.get(target_stage, 'research-questions/')

    # Build the full URL since we're nested under /project/<project_id>/design/
    full_url = f'/project/{project_id}/design/{relative_path}'

    return redirect(full_url)
