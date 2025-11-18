import json
from django.contrib import messages
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import get_user_model
from apps.design.exceptions.research_question_exceptions import QuestionSubmissionError
from apps.design.research_question.models.research_question import ResearchQuestion
from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.design.search_strategy.services.keyword_processor_service import KeywordProcessorService
from apps.project.models import Project
from apps.project.services.project_services import ProjectService

# Create your views here.

research_question_service = ResearchQuestionService()
project_service = ProjectService()
keyword_processor_service = KeywordProcessorService()



# Obtén el modelo de Usuario activo en tu proyecto
User = get_user_model()

def hello(request):
    project = get_object_or_404(Project, pk =1)  # Reemplaza '1' con el ID del proyecto que deseas obtener
    return render(request, 'base_tabs.html', {
        'project': project
    })
def open_questions_workspace_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    status_filter = request.GET.get('status', None)
    if status_filter in [ResearchQuestion.Status.DRAFT, ResearchQuestion.Status.READY_TO_SEND, ResearchQuestion.Status.SUGGESTED]:
        questions = research_question_service.get_research_questions_by_status(
            project=project, 
            status=status_filter
        )
    else:
        questions = research_question_service.get_all_questions_by_user_and_project(
            user=request.user, 
            project_id=project_id
        )
    project_keywords = keyword_processor_service.get_project_keywords(project)
    
    context = {
        'project': project, # Añadir el proyecto al contexto
        'questions': questions,
        'keywords': project_keywords,
        'active_tab': 'questions_history', 
    }
    return render(request, 'research_question_workspace.html', context)

def create_research_question(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    
    context = {
        'project': project,
        'active_tab': 'questions_history',
    }
    return render(request, 'create_research_question.html', context)

def send_research_question_for_review(request, question_id):
    try:
        question = research_question_service.get_research_question_by_id(question_id, request.user)
    except ResearchQuestion.DoesNotExist:
        raise Http404("Research question not found")
    project_id = question.project.id
    try:
        research_question_service.submit_research_question_for_review(question)
        messages.success(request, "La pregunta ha sido enviada para revisión.")
    except QuestionSubmissionError as e:
        messages.warning(request, str(e))
    
    return redirect('design:questions_history', project_id=project_id)
    
def edit_research_question(request, question_id):
    question = get_object_or_404(ResearchQuestion, id=question_id)
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
        'project': project,  # Siempre pasamos el proyecto
        'question_json': json.dumps(question_data),
        'active_tab': 'questions_history',
    }
    return render(request, 'create_research_question.html', context)

def delete_research_question(request, question_id):
    try:
        question = research_question_service.get_research_question_by_id(question_id, request.user)
        project_id = question.project.id  # Obtener el project_id antes de eliminar
        question.delete()
        return redirect('design:questions_history', project_id=project_id)
    except ResearchQuestion.DoesNotExist:  # Cambiado de question.DoesNotExist
        raise Http404("Research question not found")
    
def autosave_research_question(request):
    if request.method == 'POST':
        try:
            project_id = request.POST.get('project_id')
            if not project_id:
                raise ValueError("Project ID is missing.")
            
            question = research_question_service.autosave_question(request.POST, request.user, project_id)
            keyword_processor_service.suggest_and_store_key_terms(research_question = question)
            current_status = research_question_service.define_status(question)
            # Return the new ID and status, as expected by the frontend script
            return JsonResponse({'id': question.id, 'status': question.status, 'can_submit': research_question_service.can_submit_question(question)})
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400) # Bad Request
        except Exception as e:
            # Catch any other potential errors during save
            return JsonResponse({'error': 'An unexpected error occurred.'}, status=500)
    return JsonResponse({'error': 'Invalid request method.'}, status=405) # Method Not Allowed

def get_framework_fields(request, framework_id):
    try:
        framework = research_question_service.get_framework_by_id(framework_id)
        field_names = list(framework.fields_data.keys())
        return JsonResponse({'fields': field_names})
    except framework.DoesNotExist:
        return JsonResponse({'error': 'Framework not found'}, status=404)