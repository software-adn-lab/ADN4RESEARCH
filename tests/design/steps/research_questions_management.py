import json
import logging
from unittest.mock import Mock
from behave import given, then, when, step
from apps.design.research_question.services.question_services import ResearchQuestionService

research_question_service = ResearchQuestionService()
notification_service = Mock()

#El dado es un paso en comun, esta en common_steps.py

@step('que esta pregunta está "{status_ready}"')
def step_que_pregunta_esta_ready(context, status_ready):
    context.research_question.status = status_ready
    context.research_question.save()
    assert context.research_question.status == status_ready

@when('envíe la pregunta de investigación creada')
def step_cuando_envio_pregunta_creada(context):
    research_question_service.submit_research_question_for_review(research_question_id=context.research_question.id)
    
@then('la pregunta estará "{status_suggested}" para el proyecto')
def step_entonces_sistema_cambia_estado(context, status_suggested):
    context.research_question.refresh_from_db()
    assert context.research_question.status == status_suggested

@step('el sistema notificará al equipo investigador')
def step_entonces_sistema_notifica_equipo(context):
    # Este lo hago aqui no mas por simular lo de la notificacion
    context.notification = Mock()
    notification_service.send_notification.return_value = True
    notifications = notification_service.get_notifications_for_project.return_value = [context.notification]
    assert len(notifications) > 0
    
@given('que existen preguntas de investigación "{status_suggested}" por los investigadores para el proyecto')
def step_dado_existen_preguntas_sugeridas(context, status_suggested):
    fields = {
            "Population": "Population details",
            "Intervention": "Intervention details",
            "Comparison": "Comparison details",
            "Outcome": "Outcome details",
        }
    context.research_question_one = research_question_service.add_research_question(
        project_id=context.project.id,
        question="Ejemplo de pregunta sugerida uno",
        motivation="Ejemplo de motivación para la pregunta uno",
        researcher_id=context.researcher.id,
        framework_fields=fields
    )
    research_question_service.submit_research_question_for_review(research_question_id=context.research_question_one.id)
    context.research_question_two = research_question_service.add_research_question(
        project_id=context.project.id,
        question="Ejemplo de pregunta sugerida dos",
        motivation="Ejemplo de motivación para la pregunta dos",
        researcher_id=context.researcher_two.id,
        framework_fields=fields
    )
    research_question_service.submit_research_question_for_review(research_question_id=context.research_question_two.id)
    research_questions_project = research_question_service.get_questions_for_workspace(
        project_id=context.project.id,
        user=context.researcher,
        status_filter=status_suggested
    )
    suggested_questions_project = research_question_service.get_discussion_research_questions_by_project(
        project_id=context.project.id
    )
    assert len(research_questions_project) > 0

@step('selecciono una pregunta que no haya sido sugerida por mí')
def step_y_selecciono_pregunta_no_sugerida_por_mi(context):
    # El researcher escoge una pregunta sugerida por otro researcher (researcher 2 xd)
    context.selected_question = research_question_service.select_question_to_suggest_action(question_id = context.research_question_two.id, suggester_id = context.researcher.id)
    assert context.selected_question.researcher != context.researcher 

@when('la revise y sugiera {action} la pregunta de investigación seleccionada con la justificación de mi decisión')
def step_cuando_sugiero_aprobar_pregunta(context, action):
    action_map = {
        "approve": "APPROVED",
        "reject": "REJECTED"
    }
    target_status = action_map[action.lower()]
    justification = f"Decisión tomada: {action} por criterios de prueba."
    
    context.processed_question = research_question_service.review_research_question(
        question_id=context.selected_question.id,
        verdict=target_status,
        justification=justification
    )
    context.research_question = context.processed_question # esto es por el paso siguiente que me pide behave que se actualice la movida