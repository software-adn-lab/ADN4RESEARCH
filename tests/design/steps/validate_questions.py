from behave import given, when, then, step
from django.contrib.auth.models import User
from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.design.research_question.models.research_question import ResearchQuestion
import logging
from django.core.exceptions import ValidationError

research_question_service = ResearchQuestionService()

@given('que existen preguntas en el proyecto como:')
def step_dado_existen_preguntas_sugeridas(context):
    fields = {
            "Population": "Population details",
            "Intervention": "Intervention details",
            "Comparison": "Comparison details",
            "Outcome": "Outcome details",
        }
    for row in context.table:
        desired_status = row['estado']
        question_text = row['pregunta']
        rq = research_question_service.add_research_question(
            project_id=context.project.id,
            question=question_text,
            motivation="Setup automático",
            researcher_id=context.researcher.id,
            framework_fields=fields
        )
        # bypasseo de validaciones para setear el estado directamente
        status_enum = getattr(ResearchQuestion.Status, desired_status)
        rq.status = status_enum
        rq.save()
    assert context.project.research_questions.count() > 0
    
@when('consolide el estado de las preguntas de investigación de mi proyecto')
def step_cuando_consolido_estado_preguntas(context):
    stats = research_question_service.consolidate_questions(
        project_id=context.project.id,
        user=context.owner 
    )
    assert stats["total_approved"] > 0

@then('las preguntas de investigación "APPROVED" deben ser parte del protocolo de diseño del proyecto')
def step_preguntas_approved_son_protocolo(context):
    protocol_qs = context.project.protocol_questions
    protocol_texts = [rq.question for rq in protocol_qs]
    approved_question_expected = "Pregunta A"
    assert approved_question_expected in protocol_texts

@step('las preguntas "SUGGESTED" deben cambiar automáticamente a "REJECTED"')
def step_preguntas_sugeridas_son_rechazadas(context):
    suggested_questions = context.project.research_questions.filter(status=ResearchQuestion.Status.SUGGESTED)
    assert suggested_questions.count() == 0

@step('solo el owner del proyecto podrá cambiar las preguntas o su estado, bloqueando a los investigadores')
def step_solo_owner_puede_cambiar_preguntas(context):
    target_question = context.project.research_questions.first()
    try:
        # Intentamos cambiar una pregunta usando al investigador
        research_question_service.update_research_question(
            question_id=target_question.id,
            user=context.researcher,
            question="Intento de edición", 
            motivation="Intento de saltar el bloqueo"
        )
        assert False # Si es false entonces no se cambio la pregunta por el investigador
    except ValidationError:
        pass 

    texto_owner = "Edición autorizada del Owner"
    try:
        research_question_service.update_research_question(
            question_id=target_question.id,
            user=context.owner,
            question=texto_owner,
            motivation="Corrección post-consolidación"
        )
    except ValidationError as e:
        assert False, f"FALLO DE ACCESO: El owner debería poder editar, pero recibió error: {e}"
