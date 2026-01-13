"""
Vistas para resolución de discrepancias.
Responsable de resolver conflictos entre revisores.
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required

from apps.project.structure.models.project_models import Project
from apps.selection.models import (
    SelectionPhase, PaperAssignment, PaperReview,
    SelectionStageChoices, SelectionDecisionChoices
)


@login_required
def discussion_view(request, project_id):
    """
    Página de discusión - resolución de conflictos.
    
    Muestra papers con decisiones conflictivas entre revisores.
    """
    project = get_object_or_404(Project, id=project_id)
    selection_phase = get_object_or_404(SelectionPhase, project=project)

    # Find papers with conflicts (different decisions from different researchers)
    conflicts = []
    all_papers = PaperAssignment.objects.filter(
        selection_phase=selection_phase
    ).values('paper_id').distinct()

    for paper in all_papers:
        paper_id = paper['paper_id']

        # Get all reviews for this paper
        reviews = PaperReview.objects.filter(
            assignment__paper_id=paper_id,
            assignment__selection_phase=selection_phase
        ).exclude(decision=SelectionDecisionChoices.PENDING)

        decisions = reviews.values_list('decision', flat=True)
        unique_decisions = set(decisions)

        # If more than one unique decision, it's a conflict
        if len(unique_decisions) > 1:
            conflicts.append({
                'paper_id': paper_id,
                'reviews': reviews,
                'decisions': list(unique_decisions)
            })

    context = {
        'project': project,
        'selection_phase': selection_phase,
        'conflicts': conflicts,
        'current_stage': 'discussion'
    }

    return render(request, 'discussion/discussion.html', context)
