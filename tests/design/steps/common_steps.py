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
    context.framework_name = framework_name
    context.framework = project_service.get_or_create_framework(framework_name, context.owner)
    project_service.asign_research_framework_to_project(
        project=context.project,
        framework=context.framework
    )
    assert context.project.research_framework == context.framework

@step('la etapa "{stage_name}" está abierta')
def step_etapa_abierta(context, stage_name):
    context.stage = stage_service.get_or_create_stage(context.project, stage_name)
    stage_service.open_stage(context.stage, context.owner)
    assert stage_service.is_stage_opened(stage=context.stage)

@step('la etapa se cerrará')
def step_y_etapa_cerrada(context):
    stage_service.close_stage(stage=context.stage, closed_by=context.owner)
    assert not stage_service.is_stage_opened(stage=context.stage)
