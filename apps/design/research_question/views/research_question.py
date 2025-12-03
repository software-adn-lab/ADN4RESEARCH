import json
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import get_user_model
from apps.design.exceptions.research_question_exceptions import QuestionNotFoundError, QuestionSubmissionError
from apps.design.research_question.forms import ResearchQuestionAutosaveForm
from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.design.search_strategy.services.keyword_processor_service import KeywordProcessorService
from apps.project.models import Project
from apps.project.services.project_services import ProjectService
from apps.design.shared.services.design_phase_service import DesignPhaseService
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

research_question_service = ResearchQuestionService()
project_service = ProjectService()
keyword_processor_service = KeywordProcessorService()
design_phase_service = DesignPhaseService()

# Obtén el modelo de Usuario activo en tu proyecto
User = get_user_model()

def hello(request):
    project = get_object_or_404(Project, pk =1)  # Reemplaza '1' con el ID del proyecto
    return render(request, 'base_tabs.html', {
        'project': project
    })

@login_required
def open_questions_workspace_view(request, project_id):
    status_filter = request.GET.get('status')
    project = project_service.get_project_by_id(
        project_id, 
        user=request.user, 
        related_fields=['owner', 'research_framework', 'design_phase'] 
    )
    questions = research_question_service.get_questions_for_workspace(
        project_id=project_id, 
        user=request.user,
        status_filter=status_filter
    )
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

@login_required 
def create_research_question(request, project_id):
    project = project_service.get_project_by_id(
        project_id, 
        user=request.user, 
        related_fields=['owner', 'research_framework'] 
    )
    context = {
        'project': project,
        'active_tab': 'rq_workspace',
    }
    return render(request, 'create_research_question.html', context)

@login_required
def send_research_question_for_review(request, question_id):
    try:
        question = research_question_service.get_research_question_by_id(question_id, request.user)
    except QuestionNotFoundError:
        raise Http404("Research question not found")
    project_id = question.project.id
    try:
        research_question_service.submit_research_question_for_review(question_id)
    except QuestionSubmissionError as e:
        messages.warning(request, str(e))
    
    return redirect('design:rq_workspace', project_id=project_id)

@login_required    
def edit_research_question(request, question_id):
    try:
        question = research_question_service.get_research_question_by_id(question_id, request.user)
    except QuestionNotFoundError: 
        raise Http404("Research question not found or access denied")
    project = question.project  # El proyecto de la pregunta
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

@login_required
def delete_research_question(request, question_id):
    try:
        project_id = research_question_service.delete_research_question(question_id=question_id, user=request.user)
        messages.success(request, "Research question deleted successfully.")
        return redirect('design:rq_workspace', project_id=project_id)
    except QuestionNotFoundError:
        raise Http404("Research question not found or access denied")
    
@login_required
@require_POST
def autosave_research_question(request):
    form = ResearchQuestionAutosaveForm(request.POST)
    if form.is_valid():
        try:
            cleaned_data = form.cleaned_data
            project_id = cleaned_data.get('project_id')
            question_id = cleaned_data.get('question_id')
            question = research_question_service.autosave_question(cleaned_data=cleaned_data, user=request.user, project_id=project_id, question_id=question_id)
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