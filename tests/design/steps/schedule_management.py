from behave import given, when, then
from apps.design.research_question.models.research_question import ResearchQuestion
from apps.project.structure.models.project_models import Project
from freezegun import freeze_time
from django.utils import timezone
from datetime import datetime, date
from django.contrib.auth import get_user_model


from apps.design.design_phase_logic.models.design_phase import (
    DesignPhase, DesignStagePlan, DesignStageLog
)

from apps.design.design_phase_logic.services.design_phase_service import DesignPhaseService

User = get_user_model()


@given('que existe un plan de diseño aprobado con las siguientes fechas límite:')
def step_dado_plan_aprobado(context):
    # 1. Setup Básico: Usuario
    # Usamos get_or_create para evitar errores si el usuario ya existe por otro test
    user, _ = User.objects.get_or_create(username='owner', defaults={'password': 'password'})
    context.user = user

    # 2. Setup Proyecto
    # IMPORTANTE: Guardamos el OBJETO en context.project para futuros pasos
    project = Project.objects.create(
        title="Proyecto de Tesis BDD",
        summary="Resumen autogenerado",
        motivation="Validación de cronograma",
        general_objective="Objetivo Test",
        owner=user,
        # Si tu modelo Project tiene un campo de estado o activo, asegúrate de setearlo aquí también
    )
    context.project = project        # <--- CORRECCIÓN 1: Guardamos el objeto
    context.project_id = project.id  # Mantenemos el ID por compatibilidad

    # 3. Crear la Fase de Diseño
    # CORRECCIÓN 2: Forzamos is_active=True explícitamente al crearla
    phase = DesignPhase.objects.create(
        project=project,
        is_active=True  
    )
    
    # 4. Poblar el Plan
    for row in context.table:
        stage_key = getattr(DesignPhase.DesignStage, row['etapa'])
        DesignStagePlan.objects.create(
            phase=phase,
            stage=stage_key,
            planned_start_date=datetime.strptime(row['fecha_inicio_plan'], "%Y-%m-%d").date(),
            planned_end_date=datetime.strptime(row['fecha_fin_plan'], "%Y-%m-%d").date()
        )


@given('que la fecha actual es "{date_str}"')
def step_fecha_actual(context, date_str):
    context.freezer = freeze_time(date_str)
    context.freezer.start()


@given('que la etapa activa es "{stage_name}"')
def step_etapa_activa(context, stage_name):
    context.phase = DesignPhase.objects.get(pk=context.project_id)
    target_stage = getattr(DesignPhase.DesignStage, stage_name)

    context.phase.current_stage = target_stage
    context.phase.save()

    plan = DesignStagePlan.objects.get(phase=context.phase, stage=target_stage)

    DesignStageLog.objects.create(
        phase=context.phase,
        stage=target_stage,
        start_date=timezone.now()
    )
    log = DesignStageLog.objects.last()
    log.start_date = datetime.combine(plan.planned_start_date, datetime.min.time())
    log.save()

@given('que se ha aprobado una pregunta')
def step_aprobado_pregunta(context):
    ResearchQuestion.objects.create(
            design_phase=context.phase,           
            question="pregunta aprobada",
            motivation="Setup automático de prueba BDD",
            researcher=context.researcher,
            framework_fields={"Population": "Population details",
                              "Intervention": "Intervention details",
                              "Comparison": "Comparison details",
                              "Outcome": "Outcome details",
                              },
            status="APPROVED"          
        )
    pass

@when('el owner consolide la etapa "{stage_name}"')
def step_impl(context, stage_name):
    service = DesignPhaseService()
    
    # Mapeo de strings a métodos del servicio
    if stage_name == 'RQ_CREATION':
        # Nota: Si tu servicio requiere estar en DISCUSSION para consolidar preguntas,
        # asegúrate de que el flujo sea correcto. 
        # Si RQ_CREATION es automático, ajusta esto.
        pass 
    elif stage_name == 'RQ_DISCUSSION':
        # CORRECCIÓN AQUÍ: Quitamos el 'pass' y llamamos al servicio real
        service.consolidate_research_question_stage(context.project_id, context.user)

    elif stage_name == 'CRITERIA_DEFINITION':
        service.consolidate_eligibility_criteria_stage(context.project_id, context.user)
    
    elif stage_name == 'SEARCH_STRATEGY':
        service.consolidate_search_strategy_stage(context.project_id, context.user)
        
    else:
        raise ValueError(f"Etapa no soportada en steps: {stage_name}")


@then('la etapa "{stage_name}" inicia realmente el "{date_str}"')
def step_entonces_etapa_inicia_realmente(context, stage_name, date_str):
    expected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    target_stage = getattr(DesignPhase.DesignStage, stage_name)

    log = DesignStageLog.objects.filter(
        phase_id=context.project_id,
        stage=target_stage
    ).last()

    assert log is not None, f"No se encontró log de ejecución para {stage_name}"
    real_start_date = timezone.localtime(log.start_date).date()

    assert real_start_date == expected_date, \
        f"Fecha real incorrecta. Esperada: {expected_date}, Obtenida: {real_start_date}"


@then('la fecha fin planificada de "{stage_name}" se mantiene en "{date_str}"')
def step_entonces_fecha_fin_planificada(context, stage_name, date_str):
    expected_end_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    target_stage = getattr(DesignPhase.DesignStage, stage_name)

    plan = DesignStagePlan.objects.get(
        phase_id=context.project_id,
        stage=target_stage
    )

    assert plan.planned_end_date == expected_end_date, \
        "El plan base fue modificado, lo cual viola la regla de 'Deadline Fijo'"


@then('el tiempo disponible restante para "{stage_name}" debe ser de {days:d} días')
def step_entonces_tiempo_disponible_restante(context, stage_name, days):
    target_stage = getattr(DesignPhase.DesignStage, stage_name)

    plan = DesignStagePlan.objects.get(phase_id=context.project_id, stage=target_stage)

    log = DesignStageLog.objects.filter(phase_id=context.project_id, stage=target_stage).last()

    real_start_date = timezone.localtime(log.start_date).date()

    delta = plan.planned_end_date - real_start_date
    remaining_days = delta.days

    assert remaining_days == days, \
        f"Cálculo de tiempo comprimido erróneo. Esperado: {days}, Calculado: {remaining_days} (Fin Plan: {plan.planned_end_date} - Inicio Real: {real_start_date})"

# Hook para limpiar freezegun


def after_scenario(context, scenario):
    if hasattr(context, 'freezer'):
        context.freezer.stop()
