import json
from unittest.mock import Mock
from behave import given, then, when, step
from faker import Faker
from django.contrib.auth.models import User

from apps.design.research_question.models.research_question import ResearchQuestion
from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.notification.models import Notification
from apps.project.services.project_services import ProjectService


fake = Faker()
project_service = ProjectService()
research_question_service = ResearchQuestionService()
notification_service = Mock()


@when('envie una pregunta de investigación para su revision:')
def step_cuando_envio_pregunta_revision(context):
    payload = json.loads(context.text)
    context.fields = payload["fields"]
    context.suggested_question = payload["suggested_question"]
    context.motivation = payload["motivation"]

    context.research_question = research_question_service.add_research_question(
        project=context.project,
        research_framework=context.framework,
        suggested_question=context.suggested_question,
        motivation=context.motivation,  
        researcher=context.researcher,
        framework_fields=context.fields
    )
    research_question_service.submit_research_question_for_review(research_question=context.research_question)
    assert context.research_question.status == context.research_question.Status.SUGGESTED

@then('el sistema notificara la creacion al equipo investigador')
def step_entonces_sistema_notifica_equipo(context):
    context.notification = Notification.objects.create(
        type="RESEARCH_QUESTION_SUBMITTED_FOR_REVIEW",
        project=context.project,
        sender=context.researcher
    )
    notification_service.send_notification.return_value = True
    notifications = notification_service.get_notifications_for_project.return_value = [context.notification]
    assert len(notifications) > 0
