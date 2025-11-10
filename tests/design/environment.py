
from faker import Faker
from django.contrib.auth.models import User
from apps.project.models import Project
from apps.project.services.project_services import ProjectService
from apps.design.research_question.services.question_services import ResearchQuestionService

fake = Faker()

def before_scenario(context, scenario):
    """
    this method sets up a default project, owner, and researcher.
    """
    context.project_service = ProjectService()


    # Create users
    context.owner = User.objects.create_user(username=fake.user_name(), email=fake.email())
    context.researcher = User.objects.create_user(username=fake.user_name(), email=fake.email())

    # Create a Project
    context.project = Project.objects.create(
        name="Test Project",
        description="This is a test project description",
        owner=context.owner
    )

    # Add members to the project
    context.project_service.add_member(project=context.project, user=context.owner, role="OWNER")
    context.project_service.add_member(project=context.project, user=context.researcher, role="RESEARCHER")
