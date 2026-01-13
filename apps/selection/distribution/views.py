"""
Vistas para la feature de distribución de papers.
Responsable de distribuir papers entre investigadores.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods

from apps.project.structure.models.project_models import Project
from apps.selection.models import SelectionPhase, PaperAssignment
from apps.selection.services import PaperDistributionService


@login_required
def overview(request, project_id):
    """
    Página de overview - muestra distribución de papers y estado del equipo.
    """
    project = get_object_or_404(Project, id=project_id)

    # Get or create selection phase
    selection_phase, created = SelectionPhase.objects.get_or_create(
        project=project,
        defaults={'status': 'ON_GOING', 'current_stage': 'OVERVIEW'}
    )

    # Check if user is owner
    is_owner = request.user == project.owner

    # Get current user's progress
    user_assignments = PaperAssignment.objects.filter(
        selection_phase=selection_phase,
        researcher=request.user
    )

    user_total = user_assignments.count()
    from apps.selection.models import PaperReview, SelectionStageChoices, SelectionDecisionChoices
    
    user_reviews = PaperReview.objects.filter(
        assignment__in=user_assignments,
        stage=SelectionStageChoices.SCREENING
    )
    user_included = user_reviews.filter(decision=SelectionDecisionChoices.INCLUDED).count()
    user_excluded = user_reviews.filter(decision=SelectionDecisionChoices.EXCLUDED).count()
    user_pending = user_total - user_included - user_excluded
    user_percentage = int((user_reviews.exclude(decision=SelectionDecisionChoices.PENDING).count() / user_total * 100) if user_total > 0 else 0)

    # Calculate percentages for user's donut chart
    if user_total > 0:
        user_pending_pct = int((user_pending / user_total) * 100)
        user_included_pct = int((user_included / user_total) * 100)
        user_excluded_pct = 100 - user_pending_pct - user_included_pct
    else:
        user_pending_pct = 0
        user_included_pct = 0
        user_excluded_pct = 0

    # Get team progress (excluding current user)
    from apps.project.structure.models.project_models import Membership
    
    researchers = Membership.objects.filter(
        project=project,
        role='RESEARCHER'
    ).select_related('user').exclude(user=request.user)

    team_progress = []
    for membership in researchers:
        assignments = PaperAssignment.objects.filter(
            selection_phase=selection_phase,
            researcher=membership.user
        )

        total_assigned = assignments.count()
        reviews = PaperReview.objects.filter(
            assignment__in=assignments,
            stage=SelectionStageChoices.SCREENING
        )

        included_count = reviews.filter(decision=SelectionDecisionChoices.INCLUDED).count()
        excluded_count = reviews.filter(decision=SelectionDecisionChoices.EXCLUDED).count()
        pending_count = total_assigned - included_count - excluded_count
        reviewed_count = included_count + excluded_count

        # Calculate percentages for bar widths
        if total_assigned > 0:
            pending_pct = int((pending_count / total_assigned) * 100)
            included_pct = int((included_count / total_assigned) * 100)
            excluded_pct = 100 - pending_pct - included_pct
            percentage = int((reviewed_count / total_assigned) * 100)
        else:
            pending_pct = 0
            included_pct = 0
            excluded_pct = 0
            percentage = 0

        team_progress.append({
            'researcher': membership.user,
            'total_assigned': total_assigned,
            'pending': pending_count,
            'included': included_count,
            'excluded': excluded_count,
            'reviewed': reviewed_count,
            'percentage': percentage,
            'pending_pct': pending_pct,
            'included_pct': included_pct,
            'excluded_pct': excluded_pct
        })

    # Overall progress
    total_papers = PaperAssignment.objects.filter(selection_phase=selection_phase).values('paper_id').distinct().count()

    context = {
        'project': project,
        'selection_phase': selection_phase,
        'is_owner': is_owner,
        'team_progress': team_progress,
        'total_papers': total_papers,
        'user_progress': {
            'total': user_total,
            'pending': user_pending,
            'included': user_included,
            'excluded': user_excluded,
            'percentage': user_percentage,
            'pending_pct': user_pending_pct,
            'included_pct': user_included_pct,
            'excluded_pct': user_excluded_pct
        },
        'current_stage': 'overview'
    }

    return render(request, 'distribution/overview.html', context)


@login_required
@require_http_methods(['POST'])
def distribute_papers(request, project_id):
    """
    Ejecutar algoritmo de distribución de papers.
    """
    project = get_object_or_404(Project, id=project_id)

    # Only owner can distribute
    if request.user != project.owner:
        messages.error(request, 'Only project owner can distribute papers')
        return redirect('selection:overview', project_id=project_id)

    selection_phase = get_object_or_404(SelectionPhase, project=project)

    try:
        # Execute distribution
        service = PaperDistributionService(project_id)
        distribution = service.distribute_papers(total_reviews_per_paper=2)

        # Clear existing assignments
        PaperAssignment.objects.filter(selection_phase=selection_phase).delete()

        # Create new assignments
        from django.contrib.auth import get_user_model
        User = get_user_model()

        for username, paper_ids in distribution.items():
            researcher = User.objects.get(username=username)

            for paper_id in paper_ids:
                PaperAssignment.objects.create(
                    selection_phase=selection_phase,
                    paper_id=paper_id,
                    researcher=researcher
                )

        messages.success(request, f'Papers distributed successfully! {len(distribution)} researchers assigned.')

    except Exception as e:
        messages.error(request, f'Distribution failed: {str(e)}')

    return redirect('selection:overview', project_id=project_id)
