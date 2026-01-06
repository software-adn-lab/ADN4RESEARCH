from django.shortcuts import render, redirect
from django.urls import reverse
from apps.design.design_phase_logic.selectors import DesignPhaseSelector
from apps.design.design_phase_logic.models.design_phase import DesignPhase
from apps.design.research_question.selectors import ResearchQuestionSelector
from apps.design.eligibility_criteria.selectors import EligibilityCriterionSelector
from apps.design.search_strategy.selectors import SearchStrategySelector
# REFACTORED: Import decorator from shared module
from apps.shared.decorators import project_member_required


def _get_stage_url(stage_code: str, project_id: int) -> str:
    """Map stage code to appropriate workspace URL."""
    stage_urls = {
        'RQ_CREATION': 'design:questions:workspace',
        'RQ_DISCUSSION': 'design:discussion:panel',
        'ELIGIBILITY': 'design:criteria:panel',
        'SEARCH_STRATEGY': 'design:strategies:panel',
        'FINISHED': 'design:dashboard',  # Stay on dashboard
    }
    url_name = stage_urls.get(stage_code, 'design:dashboard')
    return reverse(url_name, kwargs={'project_id': project_id})


@project_member_required
def dashboard_view(request, project_id, project_dto):
    """
    Design Dashboard - Shows current stage and protocol metrics.

    Displays:
    - Current design stage (clickeable title)
    - Count of approved research questions
    - Count of approved inclusion and exclusion criteria
    - Count of approved search strategies

    CHANGED: project parameter is now project_dto (dict from IProjectManagement)
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
    approved_questions = ResearchQuestionSelector.count_approved(project_id)
    approved_inclusion = EligibilityCriterionSelector.count_approved_inclusion(project_id)
    approved_exclusion = EligibilityCriterionSelector.count_approved_exclusion(project_id)
    approved_strategies = SearchStrategySelector.count_approved(project_id)

    context = {
        'project_dto': project_dto,
        'project_id': project_id,
        'current_stage': current_stage,
        'stage_display': stage_display,
        'stage_url': stage_url,
        'metrics': {
            'questions': approved_questions,
            'inclusion_criteria': approved_inclusion,
            'exclusion_criteria': approved_exclusion,
            'search_strategies': approved_strategies,
        }
    }
    return render(request, 'design/dashboard.html', context)
