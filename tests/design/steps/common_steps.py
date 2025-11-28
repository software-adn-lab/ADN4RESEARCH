from behave import given, step
from django.contrib.auth.models import User
from apps.project.services.project_services import ProjectService
import logging
import json
from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.design.shared.models.design_phase import DesignPhase
from apps.project.services.project_services import ProjectPhaseService

research_question_service = ResearchQuestionService()

project_service = ProjectService()
project_phase_service = ProjectPhaseService()

@given('que estoy asignado a un proyecto de investigación')
def step_dado_proyecto_asignado(context):
    project_members = project_service.get_members(project=context.project)
    assert context.researcher in [member.user for member in project_members]

@step('el proyecto tiene como framework investigativo a {framework_name}')
def step_y_proyecto_con_framework(context, framework_name):
    assert context.project.research_framework.name == framework_name
    
@given('que he redactado una pregunta de investigación completa para el proyecto:')
def step_dado_he_redactado_pregunta(context):
    payload = json.loads(context.text)
    context.framework_fields = payload["framework_fields"]
    context.question = payload["question"]
    context.motivation = payload["motivation"]

    context.research_question = research_question_service.add_research_question(
        project_id=context.project.id,
        question=context.question,
        motivation=context.motivation,
        researcher_id=context.researcher.id,
        framework_fields=context.framework_fields
    )
    assert context.research_question is not None

@given('que la etapa de "{design_stage_name}" esta activa en la fase de diseño')
def step_dado_proyecto_en_fase_y_etapa(context, design_stage_name):
    # 1. Mapeo de Lenguaje Natural (Gherkin) -> Enums del Modelo
    stage_map = {
        "creación": DesignPhase.DesignStage.RQ_CREATION,
        "discusión": DesignPhase.DesignStage.RQ_DISCUSSION,
        "criterios": DesignPhase.DesignStage.CRITERIA_DEFINITION,
        "estrategia": DesignPhase.DesignStage.SEARCH_STRATEGY,
        "finalizado": DesignPhase.DesignStage.FINISHED,
    }
    target_stage = stage_map[design_stage_name]
    phase, created = DesignPhase.objects.update_or_create(
        project=context.project, 
        defaults={
            'current_stage': target_stage,
            'is_active': True,
        }
    )
    assert phase.current_stage == target_stage

@step('que la fase de diseño esta activa')
def step_dado_fase_diseno_activa(context):
    phase, created = DesignPhase.objects.update_or_create(
        project=context.project, # Al ser OneToOne con PK=True, esto busca por ID automáticamente
        defaults={
            'is_active': True,
        }
    )
    assert phase.is_active is True