from behave import given, step
from django.contrib.auth.models import User
from apps.project.services.project_services import ProjectService
from apps.project.services.stage_services import StageService

project_service = ProjectService()
stage_service = StageService()

@given('que estoy asignado a un proyecto de investigación')
def step_dado_proyecto_asignado(context):
    project_members = project_service.get_members(project=context.project)
    assert context.researcher in [member.user for member in project_members]

@step('el proyecto tiene como framework investigativo a {framework_name}')
def step_y_proyecto_con_framework(context, framework_name):
    project_id = context.project.id
    context.framework_name = framework_name
    context.framework = project_service.get_or_create_framework(framework_name, context.owner)
    project_service.asign_research_framework_to_project(
        project=context.project,
        framework=context.framework
    )
    assert context.project.research_framework == context.framework

