"""
Vistas para screening de metadatos.
Responsable de la revisión abstract-based de papers.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from apps.project.structure.models.project_models import Project
from apps.project.facade import get_project_facade
from apps.design.api import get_design_protocol
from apps.selection.features.distribution.models import SelectionPhase
from apps.selection.features.screening.models import PaperAssignment, PaperReview
from apps.selection.models.choices import SelectionDecisionChoices, AssignmentStageChoices


@login_required
def screening_view(request, project_id):
    """
    Página de screening - revisión basada en abstract.
    """
    project = get_object_or_404(Project, id=project_id)
    selection_phase = get_object_or_404(SelectionPhase, project=project)

    # Check if papers are distributed
    if not selection_phase.screening_distributed:
        messages.info(request, 'Papers have not been distributed yet. Please distribute papers first.')
        return redirect('selection:screening_overview', project_id=project_id)

    # Get papers assigned to this user for SCREENING stage
    assignments = PaperAssignment.objects.filter(
        selection_phase=selection_phase,
        researcher=request.user,
        stage=AssignmentStageChoices.SCREENING,
        is_third_reviewer=False
    )

    if not assignments.exists():
        messages.info(request, 'You have no papers assigned for screening.')
        return redirect('selection:screening_overview', project_id=project_id)

    # Get paper details from project facade
    project_facade = get_project_facade()
    paper_ids = [a.paper_id for a in assignments]

    papers = []
    protocol = get_design_protocol()

    def _normalize_criteria(criteria_list):
        normalized = []
        for c in criteria_list or []:
            cid = c.get('id') or c.get('uuid') or c.get('pk') or c.get('code') or c.get('slug')
            label = c.get('description') or c.get('text') or c.get('name') or c.get('title') or str(c)
            if cid and label:
                normalized.append({'id': str(cid), 'label': str(label)})
        return normalized

    try:
        inclusion_criteria = _normalize_criteria(protocol.get_inclusion_criteria(project_id))
    except Exception:
        inclusion_criteria = []
    try:
        exclusion_criteria = _normalize_criteria(protocol.get_exclusion_criteria(project_id))
    except Exception:
        exclusion_criteria = []

    # Extra exclusion criteria (custom)
    exclusion_extras = [
        {'id': 'NO_MATCH_INCLUSION', 'label': 'Estudio no aplicable para ningún criterio de inclusión'},
        {'id': 'OUT_OF_SCOPE', 'label': 'Estudio fuera de foco'},
    ]
    exclusion_criteria = exclusion_criteria + exclusion_extras

    # Lookup for criterion labels
    criterion_lookup = {c['id']: c['label'] for c in (inclusion_criteria + exclusion_criteria)}
    pending_count = 0

    if paper_ids:
        all_studies = project_facade.get_studies_by_project(
            project_id=project_id,
            include_metadata=True
        )

        # Filter only assigned papers
        for study in all_studies:
            if study['id'] in paper_ids:
                assignment = assignments.get(paper_id=study['id'])

                # Get existing review if any (stage = SCREENING)
                review = PaperReview.objects.filter(
                    assignment=assignment,
                    stage='SCREENING'
                ).first()

                if not review or review.decision == SelectionDecisionChoices.PENDING:
                    pending_count += 1

                papers.append({
                    'assignment': assignment,
                    'study': study,
                    'review': review,
                })

    # Show pending first, then reviewed
    papers = sorted(
        papers,
        key=lambda p: 0 if (not p['review'] or p['review'].decision == SelectionDecisionChoices.PENDING) else 1
    )

    context = {
        'project': project,
        'selection_phase': selection_phase,
        'papers': papers,
        'pending_count': pending_count,
        'current_stage': 'screening',
        'inclusion_criteria': inclusion_criteria,
        'exclusion_criteria': exclusion_criteria,
        'criterion_lookup': criterion_lookup,
    }

    return render(request, 'screening/metadata/screening.html', context)


@login_required
@require_http_methods(['POST'])
def submit_review(request, project_id, assignment_id):
    """
    Enviar decisión de revisión para un paper en screening.
    """
    assignment = get_object_or_404(PaperAssignment, id=assignment_id)

    # Verify user owns this assignment
    if assignment.researcher != request.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    # Verify it's a screening assignment
    if assignment.stage != AssignmentStageChoices.SCREENING:
        return JsonResponse({'error': 'Invalid assignment stage'}, status=400)

    notes = request.POST.get('notes', '')
    criterion_id = request.POST.get('criterion_id') or None
    criterion_label = request.POST.get('criterion_label') or None
    decision = request.POST.get('decision')

    if decision not in ['INCLUDED', 'EXCLUDED', 'PENDING']:
        return JsonResponse({'error': 'Invalid decision'}, status=400)

    # If decision is include/exclude, criterion is required
    if decision in [SelectionDecisionChoices.INCLUDED, SelectionDecisionChoices.EXCLUDED] and not criterion_id:
        return JsonResponse({'error': 'Criterion is required for this decision'}, status=400)

    review, created = PaperReview.objects.update_or_create(
        assignment=assignment,
        stage='SCREENING',
        defaults={
            'decision': decision,
            'notes': notes,
            'criterion_label': criterion_label,
            'criterion_id': criterion_id
        }
    )

    return JsonResponse({
        'success': True,
        'review_id': review.id,
        'decision': decision,
        'criterion_id': criterion_id,
        'notes': notes
    })
