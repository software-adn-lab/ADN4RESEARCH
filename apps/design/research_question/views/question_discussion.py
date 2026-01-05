from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib import messages

from apps.project.decorators import project_member_required, build_design_url
from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.design.research_question.selectors import ResearchQuestionSelector
from apps.design.design_phase_logic.services.design_phase_service import DesignPhaseService
from apps.design.design_phase_logic.models.design_phase import DesignPhase

research_question_service = ResearchQuestionService()
design_phase_service = DesignPhaseService()


@project_member_required
def question_discussion_panel_view(request, project_id, project):
    status_filter = request.GET.get('status')

    questions = ResearchQuestionSelector.get_list_for_discussion(project_id, request.user, status_filter=status_filter)
    current_stage_plan = design_phase_service.get_current_stage_plan(project_id)
    timeline_stages = design_phase_service.get_design_timeline_context(project_id)

    context = {
        'project': project,
        'questions': questions,
        'is_owner': project.owner == request.user,
        'current_stage_plan': current_stage_plan,
        'timeline_stages': timeline_stages,
        'current_status_filter': status_filter,
        'active_tab': 'question_discussion_panel',
        'current_stage_value': project.design_phase.current_stage,
        'is_editable': project.design_phase.current_stage == DesignPhase.DesignStage.RQ_DISCUSSION,
    }
    return render(request, 'question_discussion_panel.html', context)


@project_member_required
@require_POST
def review_research_question_action(request, project_id, project):
    question_id = request.POST.get('question_id')
    verdict = request.POST.get('verdict')
    justification = request.POST.get('justification')

    if not all([question_id, verdict, justification]):
        return JsonResponse({'status': 'error', 'message': 'Missing fields (Justification is required).'}, status=400)

    try:
        research_question_service.review_research_question(
            question_id=int(question_id),
            verdict=verdict,
            justification=justification,
            user_id=request.user.id
        )
        return JsonResponse({'status': 'success', 'message': 'Question reviewed successfully.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@project_member_required
@require_POST
def consolidate_discussion_stage_action(request, project_id, project):
    try:
        design_phase_service.consolidate_research_question_stage(
            project_id=project_id,
            user=request.user
        )
        msg = "Stage consolidated successfully! Questions approved and suggestions auto-rejected. Proceeding to Eligibility Criteria Definition."
        messages.success(request, msg)
        return redirect(build_design_url(project_id, 'eligibility-criteria/'))

    except Exception as e:
        messages.error(request, f"Error consolidating stage: {str(e)}")
        return redirect(build_design_url(project_id, 'discussion/'))
