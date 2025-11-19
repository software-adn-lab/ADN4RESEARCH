from django.contrib.auth.models import User
from tests.design.helpers.factories import create_project
from apps.project.services.project_services import ProjectService

def before_scenario(context, scenario):
    """
    this method sets up a default project, owner, and researcher.
    """
    project_service = ProjectService()
    context.owner = User.objects.create_user(username="owner_user")
    context.researcher = User.objects.create_user(username="researcher_user")
    context.project = project_service.create_project_with_framework(
        name = "Test Project", 
        description = "Description",
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
