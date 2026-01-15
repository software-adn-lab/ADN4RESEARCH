from django.shortcuts import render, redirect
from django.urls import reverse
from apps.design.design_phase_logic.selectors import DesignPhaseSelector
from apps.design.design_phase_logic.models.design_phase import DesignPhase
from apps.design.research_question.selectors import ResearchQuestionSelector
from apps.design.eligibility_criteria.selectors import EligibilityCriterionSelector
from apps.design.search_strategy.selectors import SearchStrategySelector
# REFACTORED: Import decorator from shared module
from apps.shared.decorators import project_member_required
# Import dashboard configuration
from .dashboard_config import DASHBOARD_STAGES


def _get_stage_status(stage_config: dict, current_stage: str) -> str:
    """
    Determine the status of a dashboard stage based on current internal stage.
    Returns: 'completed', 'active', or 'pending'
    """
    if not current_stage:
        return 'pending' if stage_config['id'] > 1 else 'active'

    # Get the flow order
    flow = DesignPhase.DESIGN_FLOW
    try:
        current_index = flow.index(current_stage)
    except ValueError:
        current_index = 0

    # Find the highest index of internal stages for this dashboard stage
    stage_indices = []
    for internal in stage_config['internal_stages']:
        try:
            stage_indices.append(flow.index(internal))
        except ValueError:
            pass

    if not stage_indices:
        return 'pending'

    max_stage_index = max(stage_indices)
    min_stage_index = min(stage_indices)

    # Determine status
    if current_index > max_stage_index:
        return 'completed'
    elif current_index >= min_stage_index:
        return 'active'
    else:
        return 'pending'


def _get_stage_url(stage_code: str, project_id: int) -> str:
    """Map stage code to appropriate workspace URL."""
    stage_urls = {
        'RQ_CREATION': 'design:questions:workspace',
        'RQ_DISCUSSION': 'design:discussion:panel',
        'CRITERIA_DEFINITION': 'design:criteria:panel',
        'SEARCH_STRATEGY': 'design:strategies:panel',
        'FINISHED': 'design:dashboard',
    }
    url_name = stage_urls.get(stage_code, 'design:dashboard')
    return reverse(url_name, kwargs={'project_id': project_id})


def _get_current_stage_number(current_stage: str) -> int:
    """Get the dashboard stage number (1-4) for the current internal stage."""
    if not current_stage:
        return 1

    for stage in DASHBOARD_STAGES:
        if current_stage in stage['internal_stages']:
            return stage['id']
    return 1


@project_member_required
def dashboard_view(request, project_id, project_dto):
    """
    Design Dashboard - Shows current stage and protocol metrics.

    Displays:
    - Project info (title, objectives)
    - Progress bar with current stage
    - 4-stage protocol overview with status and artifacts
    """
    # Get current stage from DesignPhase model
    try:
        design_phase = DesignPhase.objects.get(project_id=project_id)
        current_stage = design_phase.current_stage
        stage_display = DesignPhase.DesignStage(current_stage).label if current_stage else "Not Started"
    except DesignPhase.DoesNotExist:
        current_stage = None
        stage_display = "Not Started"

    stage_url = _get_stage_url(current_stage, project_id) if current_stage else '#'

    # Get Protocol Metrics using Selectors
    metrics = {
        'questions': ResearchQuestionSelector.count_approved(project_id),
        'inclusion_criteria': EligibilityCriterionSelector.count_approved_inclusion(project_id),
        'exclusion_criteria': EligibilityCriterionSelector.count_approved_exclusion(project_id),
        'search_strategies': SearchStrategySelector.count_approved(project_id),
    }

    # Build stages data for template
    stages = []
    for stage_config in DASHBOARD_STAGES:
        status = _get_stage_status(stage_config, current_stage)

        # Build artifacts with counts
        artifacts = []
        for artifact in stage_config['artifacts']:
            artifact_data = {
                'label': artifact['label'],
                'static': artifact.get('static', False),
            }
            if not artifact.get('static'):
                artifact_data['count'] = metrics.get(artifact['key'], 0)
            artifacts.append(artifact_data)

        stages.append({
            'id': stage_config['id'],
            'title': stage_config['title'],
            'status': status,
            'url': reverse(stage_config['url_name'], kwargs={'project_id': project_id}),
            'artifacts': artifacts,
        })

    # Calculate progress
    current_stage_number = _get_current_stage_number(current_stage)
    total_stages = len(DASHBOARD_STAGES)
    progress_percentage = ((current_stage_number - 1) / total_stages) * 100 + (25 if current_stage else 0)

    # URL for next phase (Selection)
    next_phase_url = f'/project/{project_id}/selection/'
    all_stages_completed = all(stage['status'] == 'completed' for stage in stages)

    context = {
        'project_dto': project_dto,
        'project_id': project_id,
        'current_stage': current_stage,
        'stage_display': stage_display,
        'stage_url': stage_url,
        'stages': stages,
        'current_stage_number': current_stage_number,
        'total_stages': total_stages,
        'progress_percentage': min(progress_percentage, 100),
        'metrics': metrics,
        'next_phase_url': next_phase_url,
        'all_stages_completed': all_stages_completed,
    }
    return render(request, 'dashboard.html', context)
