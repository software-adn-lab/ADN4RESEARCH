import json
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.design.design_phase_logic.services.design_phase_service import DesignPhaseService
from apps.design.design_phase_logic.selectors import DesignPhaseSelector
from apps.project.decorators import project_member_required, build_design_url
from apps.design.exceptions.research_question_exceptions import QuestionNotFoundError, QuestionSubmissionError, ResearchQuestionError
from apps.design.research_question.forms import ResearchQuestionAutosaveForm
from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.design.research_question.selectors import ResearchQuestionSelector
from apps.design.search_strategy.services.nlp.keyword_processor_service import KeywordProcessorService
from apps.project.structure.services.project_services import ProjectService

research_question_service = ResearchQuestionService()
keyword_processor_service = KeywordProcessorService()
design_phase_service = DesignPhaseService()


@project_member_required
def open_questions_workspace_view(request, project_id, project):
    status_filter = request.GET.get('status')

    questions = ResearchQuestionSelector.get_list_for_workspace(
        project_id=project_id,
        user=request.user,
        status_filter=status_filter
    )

    project_service = ProjectService()
    project_keywords = project_service.get_project_keyterms(project_id)

    # Updated to use Selector for read operations
    current_stage_plan = DesignPhaseSelector.get_current_stage_plan(project_id)
    timeline_stages = DesignPhaseSelector.get_design_timeline_context(project_id)

    context = {
        'project': project,
        'questions': questions,
        'keywords': project_keywords,
        'current_stage_plan': current_stage_plan,
        'timeline_stages': timeline_stages,
        'active_tab': 'rq_workspace',
        'current_status_filter': status_filter,
        'is_owner': project.owner == request.user,
        'current_stage': project.design_phase.current_stage,
    }
    return render(request, 'rq_workspace.html', context)


@project_member_required
def create_research_question(request, project_id, project):
    context = {
        'project': project,
        'active_tab': 'rq_workspace',
    }
    return render(request, 'create_research_question.html', context)


@project_member_required
def send_research_question_for_review(request, project_id, question_id, project):
    # We use the selector to check existence, but the service to perform the action
    question = ResearchQuestionSelector.get_by_id(question_id, request.user)
    if not question:
        raise Http404("Research question not found")

    try:
        research_question_service.submit_research_question_for_review(question_id)
        
        # Notify project owner
        try:
            from apps.notification.models import Notification
            if project.owner_id != request.user.id:
                Notification.objects.create(
                    recipient=project.owner,
                    sender=request.user,
                    type='RESEARCH_QUESTION_SUBMITTED_FOR_REVIEW',
                    title='New Research Question for Review',
                    custom_message=f'{request.user.get_full_name() or request.user.username} has submitted a research question for your review.',
                    project=project
                )
        except Exception:
            pass
        
    except QuestionSubmissionError as e:
        messages.warning(request, str(e), extra_tags='design')

    return redirect(build_design_url(project_id, 'research-questions/'))


@project_member_required
def edit_research_question(request, project_id, question_id, project):
    question = ResearchQuestionSelector.get_by_id(question_id, request.user)
    if not question:
        raise Http404("Research question not found or access denied")

    # DTO to Dict for JSON serialization
    question_data = {
        "id": question.id,
        "suggested_question": question.question,
        "motivation": question.motivation,
        "framework_fields": question.framework_fields,
        "status": question.status,
    }

    context = {
        'question': question,
        'project': project,
        'question_json': json.dumps(question_data),
        'active_tab': 'rq_workspace',
    }
    return render(request, 'create_research_question.html', context)


@project_member_required
def delete_research_question(request, project_id, question_id, project):
    question = ResearchQuestionSelector.get_by_id(question_id, request.user)
    if not question:
        raise Http404("Research question not found or access denied")

    try:
        research_question_service.delete_research_question(question_id=question_id, user=request.user)
        messages.success(request, "Research question deleted successfully.", extra_tags='design')
    except ResearchQuestionError as e:
        messages.error(request, str(e), extra_tags='design')

    return redirect(build_design_url(project_id, 'research-questions/'))


@project_member_required
@require_POST
def autosave_research_question(request, project_id, project):
    form = ResearchQuestionAutosaveForm(request.POST)
    if form.is_valid():
        try:
            cleaned_data = form.cleaned_data
            question_id = cleaned_data.get('question_id')
            question = research_question_service.autosave_question(
                cleaned_data=cleaned_data,
                user=request.user,
                project_id=project_id,
                question_id=question_id
            )
            keyword_processor_service.suggest_and_store_key_terms(research_question_id=question.id)
            can_submit = research_question_service.can_submit_question(research_question_id=question.id)

            return JsonResponse({
                'id': question.id,
                'status': question.status,
                'can_submit': can_submit,
                'message': 'Autosaved successfully'
            }, status=200)

        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Internal Error: {str(e)}'}, status=500)
    else:
        return JsonResponse({'errors': form.errors}, status=400)


@project_member_required
@require_POST
def consolidate_creation_stage_view(request, project_id, project):
    try:
        if project.owner != request.user:
            messages.error(request, "Only the project owner can consolidate the stage.", extra_tags='design')
            return redirect(build_design_url(project_id, 'research-questions/'))

        design_phase_service.consolidate_creation_stage(project_id, request.user)
        messages.success(request, "Stage consolidated successfully! Discussion Phase started.", extra_tags='design')

        return redirect(build_design_url(project_id, 'discussion/'))

    except Exception as e:
        messages.error(request, f"Error consolidating stage: {str(e)}", extra_tags='design')
        return redirect(build_design_url(project_id, 'research-questions/'))
