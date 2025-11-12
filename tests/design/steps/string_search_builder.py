from behave import given, then, when, step
from faker import Faker
from django.contrib.auth.models import User
from apps.project.services.project_services import ProjectService
from apps.design.research_question.services.question_services import ResearchQuestionService

fake = Faker()

project_service = ProjectService()
research_question_service = ResearchQuestionService()


@given('que tengo al menos una pregunta de investigación "{status}"')
def step_dado_tengo_pregunta_investigacion(context, status):
    # servicio crea la pregunta de investigacion
    fields = {
        "P": "value1",
        "I": "value2",
        "C": "value2",
        "O": "value2"
    }
    context.research_question = research_question_service.add_research_question(
        project=context.project,
        research_framework=context.project.research_framework,
        suggested_question="ESTA ES UNA PREGUNTA DE PRUEBA",
        motivation="Motivación de prueba",
        researcher=context.researcher,
        framework_fields=fields
    )
    # Verifico que tengo al menos una pregunta con ese estado
    assert context.research_question.status == status


@step('he identificado las palabra clave de la pregunta')
def step_y_he_identificado_sinonimos(context):
    
    pass


@when('pruebe una sugerencia de cadena de búsqueda para la pregunta')
def step_cuando_pruebo_sugerencia_cadena_busqueda(context):
    pass


@then('obtendré los artículos resultantes de esa cadena de búsqueda')
def step_entonces_obtendre_articulos_resultantes(context):
    pass
