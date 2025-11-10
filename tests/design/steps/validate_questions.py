from behave import step
from faker import Faker
from django.contrib.auth.models import User
from apps.project.models import Stage
from apps.project.services.project_services import ProjectService
from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.design.research_question.models.research_question import ResearchFramework, ResearchQuestion

project_service = ProjectService()
research_question_service = ResearchQuestionService()
fake =Faker()

@step('que la etapa de {nombre_etapa} está abierta')
def step_impl(context, nombre_etapa):
    context.stage = Stage.objects.create(
        project=context.project,
        name=nombre_etapa,
        status="INACTIVE"
    )
    project_service.open_stage(stage=context.stage, opened_by=context.owner, due_time=fake.future_datetime())
    
    assert project_service.is_stage_opened(stage=context.stage)

@step('que existen preguntas de investigación sugeridas por los investigadores')
def step_impl(context):
    context.framework_object = ResearchFramework.objects.create(
        name="PICO",
        fields={
            "P": "Population details",
            "I": "Intervention details",
            "C": "Comparison details",
            "O": "Outcome details",
        },
    )
    context.research_question = ResearchQuestion.objects.create(
        research_framework =context.framework_object,
        suggested_question="What is the effect of intervention X on population Y?",
        motivation="This question is important because...",
        stage=context.stage,
        researcher=context.researcher,
        project=context.project,
        status="SUGGESTED"
    )
    research_questions = research_question_service.get_research_questions_by_status(
        project=context.project,
        status="SUGGESTED"
    )
    assert len(research_questions) > 0
    
@step('apruebe el estado general de las acciones sugeridas de las preguntas de investigación')
def step_impl(context):
    
    pass

@step('se mostrarán las preguntas de investigación que fueron aprobadas')
def step_impl(context):
    pass