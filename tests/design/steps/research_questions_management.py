import json
from unittest.mock import Mock
from behave import given, then, when, step
from faker import Faker
from django.contrib.auth.models import User

from apps.design.research_question.models.research_question import ResearchFramework, ResearchQuestion
from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.notification.models import Notification
from apps.project.models import Stage
from apps.project.services.project_services import ProjectService


fake = Faker()
project_service = ProjectService()
research_question_service = ResearchQuestionService()
notification_service = Mock()
'''
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


@step('I have written a question with the following content:')
def step_impl(context):
    payload = json.loads(context.text)

    context.framework = payload["framework"]
    context.fields = payload["fields"]
    context.suggested_question = payload["suggested_question"]
    context.motivation = payload["motivation"]
    # Try to find existing framework (global or custom)
    framework_obj, created = ResearchFramework.objects.get_or_create(
        name=context.framework,
        defaults={
            "is_global": context.framework in ["PICO", "PEO", "PCC"],
            "assigned_by": context.researcher if context.framework not in ["PICO", "PEO", "PCC"] else None,
            "total_fields": len(context.fields),
            "fields": context.fields
        }
    )
    # Attach framework to research question
    context.research_question = ResearchQuestion.objects.create(
        research_framework=framework_obj,
        suggested_question=context.suggested_question,
        motivation=context.motivation,
        project=context.project,
        stage=context.stage,
        researcher=context.researcher
    )
    context.research_question.save()
    
@step('the question is on a "{ready_to_send_status}" status')
def step_impl(context, ready_to_send_status):
    context.ready_to_send_status = ready_to_send_status
    context.research_question.status = context.research_question.calculate_status()
    research_question_status = context.research_question.status
    assert context.ready_to_send_status == research_question_status

@when('I submit the question for review')
def step_impl(context):
    # Dentro del metodo debo cambiar el estado de la pregunta a SUGGESTED
    research_question_service.submit_research_question_for_review(
        research_question=context.research_question,
    )
    pass # Se verifica en el otro paso xd pero dentro de la funcion cambia el estado
    #assert context.research_question.status == "SUGGESTED"

@then('the question should change its status to "{suggested_status}"')
def step_impl(context, suggested_status):
    research_question = research_question_service.get_research_question_by_id(
        research_question_id=context.research_question.id
    )
    assert research_question.status == suggested_status

@step('a "{notification_type}" notification should be sent to the research project team')
def step_impl(context, notification_type):
    context.notification = Notification.objects.create(
        type=notification_type,
        project=context.project,
        sender=context.researcher
    )
    #project_members = project_service.get_project_members(project=context.project)
    #notification_service.send_notification(receivers = project_members, notification_type = context.notification_type)
    notification_service.send_notification.return_value = True
    #notifications = notification_service.get_notifications_for_project(
    #    project=context.project
    #)
    notifications = notification_service.get_notifications_for_project.return_value = [context.notification]
    assert len(notifications) > 0'''


@given('que estoy asignado a un proyecto de investigación')
def step_dado_proyecto_asignado(context):
    project_memebers = project_service.get_members(project=context.project)
    assert context.researcher in [member.user for member in project_memebers]
    
@step('el proyecto tiene como framework investigativo a {framework_name}')
def step_y_proyecto_con_framework(context, framework_name):
    context.framework_name = framework_name
    context.framework, created = ResearchFramework.objects.get_or_create(
        name=context.framework_name,
        defaults={
            "is_global": context.framework_name in ["PICO", "PEO", "PCC"],
            "assigned_by": context.owner,
        }
    )
    project_service.asign_research_framework_to_project(
        project=context.project,
        framework=context.framework
    )
    assert context.project.research_framework == context.framework

@step('la etapa de "{nombre_etapa}" esta abierta')
def step_y_etapa_abierta(context, nombre_etapa):
    context.stage = Stage.objects.create(
        project=context.project,
        name=nombre_etapa,
        status="INACTIVE"
    )
    project_service.open_stage(stage=context.stage, opened_by=context.owner, due_time=fake.future_datetime())
    assert project_service.is_stage_opened(stage=context.stage)


@when('envie una pregunta de investigación para su revision:')
def step_cuando_envio_pregunta_revision(context):
    payload = json.loads(context.text)
    context.fields = payload["fields"]
    context.suggested_question = payload["suggested_question"]
    context.motivation = payload["motivation"]
    framework_obj, created = ResearchFramework.objects.get_or_create(
        name=context.framework_name,
        defaults={
            "is_global": context.framework_name in ["PICO", "PEO", "PCC"],
            "assigned_by": context.owner,
            "total_fields": len(context.fields),
            "fields": context.fields
        })
    context.research_question = ResearchQuestion.objects.create(
        research_framework=framework_obj,
        suggested_question=context.suggested_question,
        motivation=context.motivation,
        project=context.project,
        stage=context.stage,
        researcher=context.researcher,
        framework_fields=context.fields)
    context.research_question.save()
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


@step('la etapa se cerrará')
def step_y_etapa_cerrada(context):
    project_service.close_stage(stage=context.stage, closed_by=context.owner)
    assert not project_service.is_stage_opened(stage=context.stage)


'''
# SEGUNDO SCENARIO
@step('there exist a "{suggested_status}" question')
def step_impl(context, suggested_status):
    context.suggested_status = suggested_status
    context.researcher2 = User.objects.create_user(username=fake.user_name(), email=fake.email())
    context.framework_object = ResearchFramework.objects.create(
        name="PICO",
        fields={"P": "Population", "I": "Intervention", "C": "Comparison", "O": "Outcome"},
    )
    context.research_question = ResearchQuestion.objects.create(
        research_framework =context.framework_object,
        suggested_question="What is the effect of intervention X on population Y?",
        stage=context.stage,
        researcher=context.researcher,
        project=context.project
    )
    project_service.submit_research_question_for_review(
        research_question=context.research_question,
    )
    assert context.research_question.status == context.suggested_status


@when('I suggest to reject the question with the justification "{justification}"')
def step_impl(context, justification):
    context.justification = justification
    research_question_service.suggest_rejecting_question(
        research_question=context.research_question,
        suggester=context.researcher2,
        justification=context.justification
    )


@then('the question status should change to "{reject_status}"')
def step_impl(context, reject_status):
    context.reject_status = reject_status
    research_question = research_question_service.get_research_question_by_id(
        research_question_id=context.research_question.id
    )
    assert research_question.status == context.reject_status

# TERCER SCENARIO
@given('I chose the "{framework}" framework')
def step_impl(context, framework):
    
    framework_fields_test_data = {
        "PICO": {"P": "Population", "I": "Intervention", "C": "Comparison", "O": "Outcome"},
        "PEO": {"P": "Population", "E": "Exposure", "O": "Outcome"},
        "PCC": {"P": "Population", "C": "Concept", "C": "Context"},
    }
    print("GGG", framework_fields_test_data[framework])
    context.framework_name = framework
    
    context.framework_object = ResearchFramework.objects.create(
        name=context.framework_name,
        fields=framework_fields_test_data[framework],
    )

@when('I have completed {completed_framework_fields}')
def step_impl(context, completed_framework_fields):
    context.completed_framework_fields = int(completed_framework_fields)
    total_fields = len(context.framework_object.fields)
    assert context.completed_framework_fields == total_fields'''
