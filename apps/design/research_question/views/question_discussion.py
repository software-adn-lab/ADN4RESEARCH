from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib import messages
from apps.project.models import Project
from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.project.services.project_services import ProjectService

from apps.design.exceptions.research_question_exceptions import QuestionReviewError

# Instancia del servicio (o inyección de dependencias si usas eso)
research_question_service = ResearchQuestionService()
project_service = ProjectService()

@login_required
def question_discussion_panel_view(request, project_id):
    project = project_service.get_project_by_id(project_id) 
    
    questions = research_question_service.get_discussion_research_questions_by_project(project_id) 
    stage_end_date = project_service.get_current_stage_deadline(project_id)
    timeline_stages = project_service.get_design_timeline_context(project_id)
    context = {
        'project': project,
        'questions': questions,
        'is_owner': project.owner == request.user,
        'stage_end_date': stage_end_date,
        'timeline_stages': timeline_stages,
        'active_tab': 'question_discussion_panel', # Para resaltar el tab si usas base_tabs active_tab == 'question_discussion_panel'
    }
    return render(request, 'question_discussion_panel.html', context)

@login_required
def select_question_to_suggest_action(request, question_id, action_type):
    try:
        # Llamamos al servicio con la acción específica
        research_question_service.process_suggestion_action(
            question_id=question_id, 
            user_id=request.user.id,
            action=action_type # Pasamos 'APPROVED' o 'REJECTED'
        )
        messages.success(request, f"Question marked as {action_type}.")
    except QuestionReviewError as e:
        messages.error(request, str(e))
    
    # Redirigir de vuelta a la lista o panel donde estaba el usuario
    return redirect('design:question_discussion_panel')

@login_required
@require_POST
def review_research_question_action(request):
    question_id = request.POST.get('question_id')
    verdict = request.POST.get('verdict') # 'APPROVED' o 'REJECTED'
    justification = request.POST.get('justification')

    if not all([question_id, verdict, justification]):
        return JsonResponse({'status': 'error', 'message': 'Missing fields.'}, status=400)
    try:
        research_question_service.review_research_question(
            question_id=int(question_id),
            verdict=verdict,
            justification=justification
        )
        return JsonResponse({'status': 'success', 'message': 'Question reviewed successfully.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def consolidate_discussion_stage_action(request, project_id):
    try:
        stats = research_question_service.consolidate_questions(
            project_id=project_id,
            user=request.user
        )
        msg = f"Stage consolidated! {stats['total_approved']} questions approved. {stats['rejected_automatically']} suggestions auto-rejected."
        messages.success(request, msg)
        return redirect('design:question_discussion_panel', project_id=project_id)
        
    except Exception as e:
        messages.error(request, f"Error consolidating stage: {str(e)}")
        return redirect('design:question_discussion_panel', project_id=project_id)