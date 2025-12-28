from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib import messages

from apps.project.decorators import project_member_required, build_design_url
from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.design.shared.services.design_phase_service import DesignPhaseService
from apps.design.design_phase_logic.models.design_phase import DesignPhase

research_question_service = ResearchQuestionService()
design_phase_service = DesignPhaseService()


@project_member_required
def question_discussion_panel_view(request, project_id, project):
    status_filter = request.GET.get('status')

    questions = research_question_service.get_discussion_research_questions_by_project(project_id, status_filter=status_filter)
    stage_end_date = design_phase_service.get_current_stage_deadline(project_id)
    timeline_stages = design_phase_service.get_design_timeline_context(project_id)

    context = {
        'project': project,
        'questions': questions,
        'is_owner': project.owner == request.user,
        'stage_end_date': stage_end_date,
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
        msg = "Stage consolidated successfully! Questions approved and suggestions auto-rejected. Proceeding to Criteria Definition."
        messages.success(request, msg)
        return redirect(build_design_url(project_id, 'discussion/'))

    except Exception as e:
        messages.error(request, f"Error consolidating stage: {str(e)}")
        return redirect(build_design_url(project_id, 'discussion/'))
