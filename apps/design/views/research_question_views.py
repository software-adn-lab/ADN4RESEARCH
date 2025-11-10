import json
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from apps.design.services.question_services import ResearchQuestionService

# Create your views here.

research_question_service = ResearchQuestionService()
from django.contrib.auth import get_user_model

# Obtén el modelo de Usuario activo en tu proyecto
User = get_user_model()

def hello(request):
    ejemplo_parametro = "valor"
    return render(request, 'base_tabs.html', {
        'parametro': ejemplo_parametro
    })

def create_research_question(request):
    frameworks = research_question_service.get_frameworks(request)
    context = {
        'frameworks': frameworks,
        'active_tab': 'questions_history',  # Agregar esto
    }
    return render(request, 'create_research_question.html', context)
 
def send_research_question_for_review(request, question_id):
    try:
        question = research_question_service.get_research_question_by_id(question_id, request.user)
        research_question_service.submit_research_question_for_review(question)
    except question.DoesNotExist:
        raise Http404("Research question not found")
    return redirect('design:questions_history')
    
def edit_research_question(request, question_id):
    try:
        question = research_question_service.get_research_question_by_id(question_id, request.user)
        frameworks = research_question_service.get_frameworks(request)
        
        # Convertimos los datos de la pregunta a JSON para pasarlos al script
        question_data = {
            "id": question.id,
            "research_framework_id": question.research_framework.id,
            "suggested_question": question.suggested_question,
            "motivation": question.motivation,
            "framework_fields": question.framework_fields,
            "status": question.status,
            "can_submit": research_question_service.can_submit_question(question) 
        }

        return render(request, 'create_research_question.html', {
            'frameworks': frameworks,
            'question': question, # Pasamos el objeto completo
            'question_json': json.dumps(question_data), # Y también en formato JSON
            'active_tab': 'questions_history',
        })
    except question.DoesNotExist:
        raise Http404("Research question not found") 

def delete_research_question(request, question_id):
    try:
        question = research_question_service.get_research_question_by_id(question_id, request.user)
        question.delete()
        return redirect('design:questions_history')
    except question.DoesNotExist:
        raise Http404("Research question not found")
    
def questions_history_view(request):
    questions = research_question_service.get_all_questions_by_user(user=request.user)
    context = {
        'questions': questions,
        'active_tab': 'questions_history', 
    }
    return render(request, 'question_history.html', context)
    
def autosave_research_question(request):
    if request.method == 'POST':
        try:
            question = research_question_service.autosave_question(request.POST, request.user)
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
        field_names = list(framework.fields.keys())
        return JsonResponse({'fields': field_names})
    except framework.DoesNotExist:
        return JsonResponse({'error': 'Framework not found'}, status=404)