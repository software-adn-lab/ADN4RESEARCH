from behave import given, step
from django.contrib.auth.models import User
from apps.project.services.project_services import ProjectService
import logging
import json
from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.project.models import ProjectPhase

research_question_service = ResearchQuestionService()

project_service = ProjectService()

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

@given('que el proyecto se encuentra en la fase de "{phase_text}" y etapa de "{stage_text}"')
def step_dado_proyecto_en_fase_y_etapa(context, phase_text, stage_text):
    # 1. Mapeo de Lenguaje Natural (Gherkin) -> Enums del Modelo
    phase_map = {
        "Diseño": ProjectPhase.PhaseType.DESIGN,
    }
    
    stage_map = {
        "Creación": ProjectPhase.Stage.RQ_CREATION,
        "Discusión": ProjectPhase.Stage.RQ_DISCUSSION, #
        "Criterios": ProjectPhase.Stage.CRITERIA_DEFINITION, # Ajusta según tu enum real si cambia
        "Finalizado": ProjectPhase.Stage.FINISHED,   #
    }

    if phase_text not in phase_map:
        raise ValueError(f"Fase desconocida en el test: '{phase_text}'. Opciones: {list(phase_map.keys())}")
    
    if stage_text not in stage_map:
        raise ValueError(f"Etapa desconocida en el test: '{stage_text}'. Opciones: {list(stage_map.keys())}")

    target_phase = phase_map[phase_text]
    target_stage = stage_map[stage_text]
    ProjectPhase.objects.update_or_create(
        project=context.project,
        phase_type=target_phase,
        defaults={
            'current_stage': target_stage,
            'is_active': True 
        }
    )