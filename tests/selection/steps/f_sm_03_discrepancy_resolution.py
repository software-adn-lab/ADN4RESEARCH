"""
BDD Steps for discrepancy resolution feature.
"""

from behave import given, when, then
from django.contrib.auth.models import User

from apps.project.structure.models.project_models import Project, Membership
from apps.selection.features.distribution.models import SelectionPhase
from apps.selection.features.screening.models import PaperAssignment, PaperReview
from apps.selection.features.discussion.models import ConflictResolution
from apps.selection.features.discussion.services import DiscrepancyResolutionService
from apps.selection.models.choices import (
    AssignmentStageChoices,
    SelectionDecisionChoices,
    SelectionStageChoices,
    SelectionStatusChoices,
)


def _normalize_stage(etapa: str) -> str:
    stage = etapa.strip().upper()
    if stage == 'FULLTEXT':
        stage = 'FULL_TEXT'
    if stage not in ('SCREENING', 'FULL_TEXT'):
        raise ValueError(f"Etapa no valida: {etapa}")
    return stage


def _map_assignment_stage(stage: str) -> str:
    return AssignmentStageChoices.SCREENING if stage == 'SCREENING' else AssignmentStageChoices.FULLTEXT


def _map_review_stage(stage: str) -> str:
    return SelectionStageChoices.STAGE_SCREENING if stage == 'SCREENING' else SelectionStageChoices.STAGE_FULLTEXT


@given('un proyecto de seleccion con un paper en conflicto de "{etapa}"')
def step_given_project_with_conflict(context, etapa):
    stage = _normalize_stage(etapa)
    assignment_stage = _map_assignment_stage(stage)
    review_stage = _map_review_stage(stage)

    owner = User.objects.create_user(username='owner', password='test123')
    project = Project.objects.create(
        title='Test Project',
        summary='Test',
        motivation='Test',
        general_objective='Test',
        owner=owner
    )
    Membership.objects.create(project=project, user=owner, role='OWNER', workload_hours=10)

    selection_phase = SelectionPhase.objects.create(
        project=project,
        status=SelectionStatusChoices.ON_GOING,
        current_stage=SelectionStageChoices.SCREENING if stage == 'SCREENING' else SelectionStageChoices.FULLTEXT
    )

    reviewer_a = User.objects.create_user(username='reviewer_a', password='test123')
    reviewer_b = User.objects.create_user(username='reviewer_b', password='test123')
    Membership.objects.create(project=project, user=reviewer_a, role='RESEARCHER', workload_hours=10)
    Membership.objects.create(project=project, user=reviewer_b, role='RESEARCHER', workload_hours=10)

    paper_id = 'PAPER-1'

    assignment_a = PaperAssignment.objects.create(
        selection_phase=selection_phase,
        paper_id=paper_id,
        researcher=reviewer_a,
        stage=assignment_stage,
        is_third_reviewer=False
    )
    assignment_b = PaperAssignment.objects.create(
        selection_phase=selection_phase,
        paper_id=paper_id,
        researcher=reviewer_b,
        stage=assignment_stage,
        is_third_reviewer=False
    )

    PaperReview.objects.create(
        assignment=assignment_a,
        decision=SelectionDecisionChoices.INCLUDED,
        stage=review_stage,
        notes='reviewer a'
    )
    PaperReview.objects.create(
        assignment=assignment_b,
        decision=SelectionDecisionChoices.EXCLUDED,
        stage=review_stage,
        notes='reviewer b'
    )

    service = DiscrepancyResolutionService(selection_phase)
    conflicts = service.get_conflicts(stage=stage)
    assert conflicts, 'Expected at least one conflict'

    context.project = project
    context.owner = owner
    context.selection_phase = selection_phase
    context.paper_id = paper_id
    context.stage = stage


@when('el director resuelve la discrepancia mediante "{mecanismo}" con decision "{decision_final}"')
def step_when_resolve_conflict(context, mecanismo, decision_final):
    service = DiscrepancyResolutionService(context.selection_phase)

    if mecanismo == 'tercer_revisor':
        third_reviewer = User.objects.create_user(username='third_reviewer', password='test123')
        Membership.objects.create(project=context.project, user=third_reviewer, role='RESEARCHER', workload_hours=10)

        result = service.assign_third_reviewer(
            paper_id=context.paper_id,
            reviewer=third_reviewer,
            stage=context.stage
        )

        service.process_third_reviewer_decision(
            assignment=result['assignment'],
            decision=decision_final,
            notes='third reviewer decision'
        )
    elif mecanismo == 'voto_owner':
        service.resolve_with_owner_vote(
            paper_id=context.paper_id,
            owner=context.owner,
            decision=decision_final,
            notes='owner vote',
            stage=context.stage
        )
    else:
        raise ValueError(f"Mecanismo no soportado: {mecanismo}")


@then('el conflicto queda marcado como resuelto con metodo "{metodo_esperado}"')
def step_then_conflict_resolved(context, metodo_esperado):
    conflict = ConflictResolution.objects.get(
        selection_phase=context.selection_phase,
        paper_id=context.paper_id,
        stage=_map_assignment_stage(context.stage)
    )
    assert conflict.is_resolved is True
    assert conflict.resolution_method == metodo_esperado
    context.conflict = conflict


@then('la decision final del paper es "{decision_final}"')
def step_then_final_decision(context, decision_final):
    conflict = getattr(context, 'conflict', None)
    if conflict is None:
        conflict = ConflictResolution.objects.get(
            selection_phase=context.selection_phase,
            paper_id=context.paper_id,
            stage=_map_assignment_stage(context.stage)
        )
    assert conflict.final_decision == decision_final


@then('el paper ya no aparece como conflicto pendiente para "{etapa}"')
def step_then_no_pending_conflict(context, etapa):
    stage = _normalize_stage(etapa)
    service = DiscrepancyResolutionService(context.selection_phase)
    conflicts = service.get_conflicts(stage=stage)
    conflict_ids = [c['paper_id'] for c in conflicts]
    assert context.paper_id not in conflict_ids
