import json
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.project.decorators import project_member_required, build_design_url
from apps.design.exceptions.research_question_exceptions import QuestionNotFoundError, QuestionSubmissionError, ResearchQuestionError
from apps.design.research_question.forms import ResearchQuestionAutosaveForm
from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.design.search_strategy.services.keyword_processor_service import KeywordProcessorService
from apps.design.shared.services.design_phase_service import DesignPhaseService

research_question_service = ResearchQuestionService()
keyword_processor_service = KeywordProcessorService()
design_phase_service = DesignPhaseService()


@project_member_required
def open_questions_workspace_view(request, project_id, project):
    status_filter = request.GET.get('status')

    questions = research_question_service.get_questions_for_workspace(
        project_id=project_id,
        user=request.user,
        status_filter=status_filter
    )
    from apps.project.structure.services.project_services import ProjectService
    project_service = ProjectService()
    project_keywords = project_service.get_project_keyterms(project_id)
    stage_end_date = design_phase_service.get_current_stage_deadline(project_id)
    timeline_stages = design_phase_service.get_design_timeline_context(project_id)

    context = {
        'project': project,
        'questions': questions,
        'keywords': project_keywords,
        'stage_end_date': stage_end_date,
        'timeline_stages': timeline_stages,
        'active_tab': 'rq_workspace',
        'current_status_filter': status_filter,
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
    try:
        question = research_question_service.get_research_question_by_id(question_id, request.user)
    except QuestionNotFoundError:
        raise Http404("Research question not found")

    try:
        research_question_service.submit_research_question_for_review(question_id)
    except QuestionSubmissionError as e:
        messages.warning(request, str(e))

    return redirect(build_design_url(project_id, 'research-questions/'))


@project_member_required
def edit_research_question(request, project_id, question_id, project):
    try:
        question = research_question_service.get_research_question_by_id(question_id, request.user)
    except QuestionNotFoundError:
        raise Http404("Research question not found or access denied")

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
    try:
        question = research_question_service.get_research_question_by_id(question_id, request.user)
    except QuestionNotFoundError:
        raise Http404("Research question not found or access denied")

    try:
        research_question_service.delete_research_question(question_id=question_id, user=request.user)
        messages.success(request, "Research question deleted successfully.")
    except ResearchQuestionError as e:
        messages.error(request, str(e))

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
