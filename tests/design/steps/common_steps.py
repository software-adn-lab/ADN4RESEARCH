from behave import given
from faker import Faker
from django.contrib.auth.models import User

from design.services.question_services import ResearchQuestionService
from project.models import Project, Stage
from project.services.project_services import ProjectService

fake = Faker()
project_service = ProjectService()
research_question_service = ResearchQuestionService()

@given('the "{stage_name}" stage of the project is opened')
def step_impl(context, stage_name):
    context.stage_name = stage_name
    context.owner = User.objects.create_user(username=fake.user_name(), email=fake.email())
    context.researcher = User.objects.create_user(username=fake.user_name(), email=fake.email())
    context.project = Project.objects.create(
        name="Test Project",
        description="This is a test project description",
        owner=context.owner
    )
    project_service.add_member(project = context.project, user = context.owner, role="OWNER")
    project_service.add_member(project = context.project, user = context.researcher, role="RESEARCHER")
    context.stage = Stage.objects.create(
        project=context.project,
        name=stage_name,
        status="INACTIVE"
    )
    due_time = fake.future_datetime()
    # Abrir la etapa solo es cambiar su estado a OPENED
    project_service.open_stage(
        stage=context.stage,
        opened_by=context.owner,
        due_time=due_time
    )
    assert project_service.is_stage_opened(stage=context.stage)