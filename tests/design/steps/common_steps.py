from behave import given, step
from django.contrib.auth.models import User
from apps.project.services.project_services import ProjectService
import logging
import json
from apps.design.research_question.services.question_services import ResearchQuestionService

research_question_service = ResearchQuestionService()

project_service = ProjectService()

@given('que estoy asignado a un proyecto de investigación')
def step_dado_proyecto_asignado(context):
    project_members = project_service.get_members(project=context.project)
    assert context.researcher in [member.user for member in project_members]

@step('el proyecto tiene como framework investigativo a {framework_name}')
def step_y_proyecto_con_framework(context, framework_name):
    assert context.project.research_framework.name == framework_name
    
@given('que he redactado una pregunta de investigación completa para el proyecto:')
def step_dado_he_redactado_pregunta(context):
    payload = json.loads(context.text)
    context.framework_fields = payload["framework_fields"]
    context.question = payload["question"]
    context.motivation = payload["motivation"]

    context.research_question = research_question_service.add_research_question(
        project_id=context.project.id,
        question=context.question,
        motivation=context.motivation,
        researcher_id=context.researcher.id,
        framework_fields=context.framework_fields
    )
    assert context.research_question is not None

