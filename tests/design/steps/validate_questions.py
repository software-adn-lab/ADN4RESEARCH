from behave import step
from faker import Faker
from django.contrib.auth.models import User
from apps.project.services.project_services import ProjectService
from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.design.research_question.models.research_question import ResearchQuestion
from apps.project.models import ResearchFramework

project_service = ProjectService()
research_question_service = ResearchQuestionService()
fake =Faker()

@given('que existen preguntas de investigación sugeridas por los investigadores')
def step_dado_existen_preguntas_sugeridas(context):
    fields = {
            "Population": "Population details",
            "Intervention": "Intervention details",
            "Comparison": "Comparison details",
            "Outcome": "Outcome details",
        }
    context.research_question_one = research_question_service.add_research_question(
        project_id=context.project.id,
        question="Ejemplo de pregunta sugerida",
        motivation="Ejemplo de motivación para la pregunta",
        researcher_id=context.researcher.id,
        framework_fields=fields
    )
    context.research_question_two = research_question_service.add_research_question(
        project_id=context.project.id,
        question="Ejemplo de pregunta sugerida",
        motivation="Ejemplo de motivación para la pregunta",
        researcher_id=context.researcher.id,
        framework_fields=fields
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