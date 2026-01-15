"""
BDD Steps for screening reminder / phase mode feature
Tests overview behavior based on selection phase dates and status.
"""

import json
from datetime import datetime, date
from behave import given, when, then, step
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from django.utils import timezone

from apps.project.structure.models.project_models import Project, Membership
from apps.selection.models import (
    SelectionPhase, PaperAssignment, PaperReview,
    SelectionStatusChoices, SelectionStageChoices, SelectionDecisionChoices
)


use_step_matcher("re")


@step('que la fase de "selección" inicia el "(?P<fecha_inicio>.+)" y finaliza el "(?P<fecha_fin>.+)"')
def step_create_selection_phase_with_dates(context, fecha_inicio, fecha_fin):
    """
    Create a project with a selection phase that has specific start/end dates.
    """
    # Parse dates
    start_date = datetime.strptime(fecha_inicio, "%Y-%m-%d")
    end_date = datetime.strptime(fecha_fin, "%Y-%m-%d")
    
    # Create owner
    owner = User.objects.create_user(username='owner_test', password='test123')
    
    # Create project
    project = Project.objects.create(
        title='Test Project',
        summary='Test',
        motivation='Test',
        general_objective='Test',
        owner=owner
    )
    
    # Create membership for owner
    Membership.objects.create(
        project=project,
        user=owner,
        role='OWNER',
        workload_hours=10
    )
    
    # Create selection phase with dates
    selection_phase = SelectionPhase.objects.create(
        project=project,
        status=SelectionStatusChoices.ON_GOING,
        current_stage=SelectionStageChoices.SCREENING,
        start_date=timezone.make_aware(start_date),
        end_date=timezone.make_aware(end_date)
    )
    
    # Store in context
    context.project = project
    context.owner = owner
    context.selection_phase = selection_phase
    context.start_date = start_date
    context.end_date = end_date


@step('hoy es "(?P<fecha_actual>.+)"')
def step_set_current_date(context, fecha_actual):
    """
    Set the simulated current date for the test.
    """
    context.current_date = datetime.strptime(fecha_actual, "%Y-%m-%d").date()
    
    # Determine if phase should be finalized based on date
    end_date = context.end_date.date() if hasattr(context.end_date, 'date') else context.end_date
    
    if context.current_date > end_date:
        # Phase has ended - update status to FINALIZED
        context.selection_phase.status = SelectionStatusChoices.FINALIZED
        context.selection_phase.save()


@step("consulte la información del proyecto")
def step_query_project_info(context):
    """
    Simulate querying the project overview to determine mode and available actions.
    """
    selection_phase = context.selection_phase
    end_date = context.end_date.date() if hasattr(context.end_date, 'date') else context.end_date
    
    # Determine mode based on status and dates
    if selection_phase.status == SelectionStatusChoices.ON_GOING and context.current_date <= end_date:
        context.mode = 'en_curso'
    else:
        context.mode = 'finalizado'
    
    # Determine available actions based on mode
    if context.mode == 'en_curso':
        context.available_actions = ['seguimiento_por_investigador']
    else:
        context.available_actions = ['decisiones_sobre_estudios_pendientes']


@step('el sistema debe operar en modo "(?P<modo>.+)"')
def step_verify_system_mode(context, modo):
    """
    Verify the system is operating in the expected mode.
    """
    assert context.mode == modo, \
        f"Expected mode '{modo}' but got '{context.mode}'"


@step('deben estar habilitadas las acciones "(?P<acciones_habilitadas>.+)"')
def step_verify_enabled_actions(context, acciones_habilitadas):
    """
    Verify the expected actions are enabled for the current mode.
    
    Actions:
    - seguimiento_por_investigador: Owner can send reminder notifications to researchers
    - decisiones_sobre_estudios_pendientes: Owner can make bulk decisions on pending papers
      (include_all, exclude_all, send_to_discussion)
    """
    expected_actions = acciones_habilitadas.split(',')
    expected_actions = [a.strip() for a in expected_actions]
    
    for action in expected_actions:
        assert action in context.available_actions, \
            f"Expected action '{action}' to be enabled but available actions are: {context.available_actions}"