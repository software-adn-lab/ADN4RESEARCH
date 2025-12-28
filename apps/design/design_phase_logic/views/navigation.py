from django.shortcuts import redirect
from django.urls import reverse
from apps.project.decorators import project_member_required
from apps.design.design_phase_logic.models.design_phase import DesignPhase


@project_member_required
def design_stages_router(request, project_id, project):
    """Router that redirects to the appropriate stage view based on query param or current stage."""
    target_stage = request.GET.get('target_stage')
    stage_map = {
        DesignPhase.DesignStage.RQ_CREATION.value: 'research-questions/',
        DesignPhase.DesignStage.RQ_DISCUSSION.value: 'discussion/',
        DesignPhase.DesignStage.CRITERIA_DEFINITION.value: 'eligibility-criteria/',
        DesignPhase.DesignStage.SEARCH_STRATEGY.value: 'search-strategy/',
    }

    relative_path = stage_map.get(target_stage, 'research-questions/')

    # Build the full URL since we're nested under /project/<project_id>/design/
    full_url = f'/project/{project_id}/design/{relative_path}'

    return redirect(full_url)
