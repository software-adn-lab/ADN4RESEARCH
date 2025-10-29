from unittest.mock import Mock
from behave import given, then, when, step
from faker import Faker
from django.contrib.auth.models import User

from apps.design.models.research_question_models import ResearchFramework, ResearchQuestion
from apps.design.services.question_services import ResearchQuestionService
from apps.project.models import Project, Stage
from apps.project.services.project_services import ProjectService
fake = Faker()
project_service = ProjectService()
research_question_service = ResearchQuestionService()
notification_service = Mock()
    
@step('there are research question versions with status "{question_status}" awaiting validation')
def step_impl(context, question_status):
    context.question_status = question_status
    context.framework_object = ResearchFramework.objects.create(
        name="PICO",
        fields={
            "P": "Population details",
            "I": "Intervention details",
            "C": "Comparison details",
            "O": "Outcome details",
        },
    )
    context.research_question = ResearchQuestion.objects.create(
        research_framework =context.framework_object,
        suggested_question="What is the effect of intervention X on population Y?",
        motivation="This question is important because...",
        stage=context.stage,
        researcher=context.researcher,
        project=context.project
    )
    expected_status = context.research_question.status = context.research_question.calculate_status()
    assert expected_status == context.question_status

@when('the owner approves the question with the justification "{justification}"')
def step_impl(context, justifications):
    pass

@then('the question status should to "{approved_status}"')
def step_impl(context):
    pass

@step('a history record should be created with approver, justification, and date')
def step_impl(context):
    pass

@step('all members of the research project should receive a notification of the approval')
def step_impl(context):
    pass