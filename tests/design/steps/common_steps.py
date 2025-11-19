from behave import given, step
from django.contrib.auth.models import User
from apps.project.services.project_services import ProjectService
import logging

project_service = ProjectService()

@given('que estoy asignado a un proyecto de investigación')
def step_dado_proyecto_asignado(context):
    project_members = project_service.get_members(project=context.project)
    assert context.researcher in [member.user for member in project_members]

@step('el proyecto tiene como framework investigativo a {framework_name}')
def step_y_proyecto_con_framework(context, framework_name):
    assert context.project.research_framework.name == framework_name

