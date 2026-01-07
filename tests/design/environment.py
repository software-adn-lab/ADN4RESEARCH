from django.contrib.auth.models import User
from tests.design.helpers.factories import create_project
from apps.project.structure.services.project_services import ProjectService
from datetime import datetime


def before_scenario(context, scenario):
    """
    this method sets up a default project, owner, and researcher.
    """
    project_service = ProjectService()
    User.objects.filter(username="owner_user").delete()
    User.objects.filter(username="researcher_user").delete()
    User.objects.filter(username="researcher_user_two").delete()

    context.owner = User.objects.create_user(username="owner_user")
    context.researcher = User.objects.create_user(username="researcher_user")
    context.researcher_two = User.objects.create_user(username="researcher_user_two")
    context.project = project_service.create_project_with_framework(
        project_title="Test Project",
        summary="Summary",
        motivation="Motivation Description",
        general_objective="General Objective Description",
        project_end_date=datetime.now(),
        owner=context.owner,
        framework_name="PICO",
        framework_fields={
            "Population": "",
            "Intervention": "",
            "Comparison": "",
            "Outcome": ""
        }
    )
    project_service.add_member(context.project, context.researcher, role="RESEARCHER")
    project_service.add_member(context.project, context.researcher_two, role="RESEARCHER")
    context.project.save()
