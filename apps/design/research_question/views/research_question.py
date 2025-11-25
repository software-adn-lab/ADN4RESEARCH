import json
from django.contrib import messages
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import get_user_model
from apps.design.exceptions.research_question_exceptions import QuestionSubmissionError
from apps.design.research_question.forms import ResearchQuestionAutosaveForm
from apps.design.research_question.models.research_question import ResearchQuestion
from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.design.search_strategy.services.keyword_processor_service import KeywordProcessorService
from apps.project.models import Project
from apps.project.services.project_services import ProjectService
from django.views.decorators.http import require_POST

research_question_service = ResearchQuestionService()
project_service = ProjectService()
keyword_processor_service = KeywordProcessorService()

# Obtén el modelo de Usuario activo en tu proyecto
User = get_user_model()

def hello(request):
    project = get_object_or_404(Project, pk =1)  # Reemplaza '1' con el ID del proyecto
    return render(request, 'base_tabs.html', {
        'project': project
    })
    
def open_questions_workspace_view(request, project_id):
    # Obtengo las preguntas del proyecto que un usuario ha creado
    questions = research_question_service.get_all_questions_by_user_and_project(project_id=project_id, user=request.user)
    # Obtengo las keywords del proyecto
    project_keywords = project_service.get_project_keyterms(project_id)
    # Obtengo el proyecto para pasarle solo cosas necesarias al template, no el objeto entero al template
    project = project_service.get_project_by_id(project_id)
    context = {
        'project': project,
        'questions': questions, # aqui si le mando todo porque son algunos atributos de las preguntas
        'keywords': project_keywords,
        'active_tab': 'questions_history', 
    }
    return render(request, 'rq_workspace.html', context)

def create_research_question(request, project_id):
    project = project_service.get_project_by_id(project_id)
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
        research_question_service.submit_research_question_for_review(question_id)
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

@require_POST
def autosave_research_question(request):
    form = ResearchQuestionAutosaveForm(request.POST)
    if form.is_valid():
        try:
            # Extraemos los datos ya limpios y tipados (Diccionarios, Enteros, Strings)
            cleaned_data = form.cleaned_data
            project_id = cleaned_data.get('project_id')
            question_id = cleaned_data.get('question_id') # Será None si es creación
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

def get_research_questions_by_status(request, project_id, status):
    questions = research_question_service.get_research_questions_by_project_and_status(project_id=project_id, status=status)
    questions_data = [
        {
            'id': q.id,
            'question': q.question,
            'motivation': q.motivation,
            'status': q.status,
            'created_at': q.created_at,
            'modified_at': q.modified_at,
        }
        for q in questions
    ]
    return JsonResponse({'questions': questions_data}, status=200)