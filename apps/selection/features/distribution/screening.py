"""
Vistas para la feature de distribución de papers.
Incluye Screening Overview y funciones auxiliares.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.utils import timezone

from apps.project.structure.models.project_models import Project, Membership
from apps.selection.features.distribution.models import SelectionPhase
from apps.selection.features.screening.models import PaperAssignment, PaperReview
from apps.selection.models.choices import (
    SelectionDecisionChoices,
    AssignmentStageChoices,
    SubPhaseStatusChoices,
    SelectionStageChoices,
)
from apps.selection.features.distribution.services import PaperDistributionService
from apps.selection.features.discussion.services import DiscrepancyResolutionService


def _calculate_progress(selection_phase, user, stage='SCREENING'):
    """
    Calculate progress for a user in a given stage.
    
    Args:
        selection_phase: SelectionPhase object
        user: User object
        stage: 'SCREENING' or 'FULLTEXT'
        
    Returns:
        Dict with progress data
    """
    assignment_stage = AssignmentStageChoices.SCREENING if stage == 'SCREENING' else AssignmentStageChoices.FULLTEXT
    review_stage = 'SCREENING' if stage == 'SCREENING' else 'FULL_TEXT'
    
    # Get user's assignments for this stage
    assignments = PaperAssignment.objects.filter(
        selection_phase=selection_phase,
        researcher=user,
        stage=assignment_stage,
        is_third_reviewer=False
    )
    
    total = assignments.count()
    
    if total == 0:
        return {
            'total': 0,
            'pending': 0,
            'included': 0,
            'excluded': 0,
            'percentage': 0,
            'pending_pct': 0,
            'included_pct': 0,
            'excluded_pct': 0
        }
    
    # Count reviews
    reviews = PaperReview.objects.filter(
        assignment__in=assignments,
        stage=review_stage
    )
    
    included = reviews.filter(decision=SelectionDecisionChoices.INCLUDED).count()
    excluded = reviews.filter(decision=SelectionDecisionChoices.EXCLUDED).count()
    reviewed = included + excluded
    pending = total - reviewed
    
    percentage = int((reviewed / total) * 100)
    pending_pct = int((pending / total) * 100)
    included_pct = int((included / total) * 100)
    excluded_pct = 100 - pending_pct - included_pct
    
    return {
        'total': total,
        'pending': pending,
        'included': included,
        'excluded': excluded,
        'percentage': percentage,
        'pending_pct': pending_pct,
        'included_pct': included_pct,
        'excluded_pct': excluded_pct
    }


def _get_team_progress(selection_phase, exclude_user, stage='SCREENING'):
    """
    Get progress for all team members except the specified user.
    """
    researchers = Membership.objects.filter(
        project=selection_phase.project,
        role__in=['OWNER', 'RESEARCHER']
    ).select_related('user').exclude(user=exclude_user)
    
    team_progress = []
    for membership in researchers:
        progress = _calculate_progress(selection_phase, membership.user, stage)
        progress['researcher'] = membership.user
        team_progress.append(progress)
    
    return team_progress


@login_required
def screening_overview(request, project_id):
    """
    Screening Overview - distribution by abstract word count and team progress.
    """
    project = get_object_or_404(Project, id=project_id)
    
    # Get or create selection phase
    selection_phase, created = SelectionPhase.objects.get_or_create(
        project=project,
        defaults={
            'status': 'ON_GOING',
            'current_stage': SelectionStageChoices.SCREENING_OVERVIEW
        }
    )
    
    is_owner = request.user == project.owner
    
    # Determine phase mode
    now = timezone.now()
    if selection_phase.screening_status == SubPhaseStatusChoices.COMPLETED:
        phase_mode = 'finalizado'
    elif selection_phase.end_date and now > selection_phase.end_date:
        phase_mode = 'finalizado'
    else:
        phase_mode = 'en_curso'
    
    # Get user progress
    user_progress = _calculate_progress(selection_phase, request.user, 'SCREENING')
    
    # Get team progress
    team_progress = _get_team_progress(selection_phase, request.user, 'SCREENING')
    
    # Count total unique papers distributed for screening
    total_papers = PaperAssignment.objects.filter(
        selection_phase=selection_phase,
        stage=AssignmentStageChoices.SCREENING,
        is_third_reviewer=False
    ).values('paper_id').distinct().count()
    
    # Check for conflicts
    discrepancy_service = DiscrepancyResolutionService(selection_phase)
    conflicts = discrepancy_service.get_conflicts(stage='SCREENING')
    conflicts_count = len(conflicts)
    
    # Check if all reviews are complete (no pending)
    all_reviews_complete = True
    if total_papers > 0:
        all_assignments = PaperAssignment.objects.filter(
            selection_phase=selection_phase,
            stage=AssignmentStageChoices.SCREENING,
            is_third_reviewer=False
        )
        for assignment in all_assignments:
            review = PaperReview.objects.filter(
                assignment=assignment,
                stage='SCREENING'
            ).first()
            if not review or review.decision == SelectionDecisionChoices.PENDING:
                all_reviews_complete = False
                break
    
    context = {
        'project': project,
        'selection_phase': selection_phase,
        'is_owner': is_owner,
        'team_progress': team_progress,
        'total_papers': total_papers,
        'user_progress': user_progress,
        'current_stage': 'screening_overview',
        'phase_mode': phase_mode,
        'conflicts_count': conflicts_count,
        'all_reviews_complete': all_reviews_complete,
        'can_finalize': all_reviews_complete and conflicts_count == 0,
    }
    
    return render(request, 'distribution/overview.html', context)


@login_required
@require_http_methods(['POST'])
def distribute_screening_papers(request, project_id):
    """
    Execute screening distribution algorithm (by abstract word count).
    """
    project = get_object_or_404(Project, id=project_id)
    
    if request.user != project.owner:
        messages.error(request, 'Only project owner can distribute papers')
        return redirect('selection:screening_overview', project_id=project_id)
    
    selection_phase = get_object_or_404(SelectionPhase, project=project)
    
    try:
        reviews_per_paper = int(request.POST.get('reviews_per_paper', 2))
        if reviews_per_paper not in [2, 3, 4]:
            reviews_per_paper = 2
        
        # Execute distribution
        service = PaperDistributionService(project_id)
        distribution = service.distribute_papers(total_reviews_per_paper=reviews_per_paper)
        
        # Clear existing screening assignments
        PaperAssignment.objects.filter(
            selection_phase=selection_phase,
            stage=AssignmentStageChoices.SCREENING
        ).delete()
        
        # Clear existing screening reviews
        PaperReview.objects.filter(
            assignment__selection_phase=selection_phase,
            stage='SCREENING'
        ).delete()
        
        # Create new assignments
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        for username, paper_ids in distribution.items():
            researcher = User.objects.get(username=username)
            
            for paper_id in paper_ids:
                PaperAssignment.objects.create(
                    selection_phase=selection_phase,
                    paper_id=paper_id,
                    researcher=researcher,
                    stage=AssignmentStageChoices.SCREENING,
                    is_third_reviewer=False
                )
        
        # Update phase status
        selection_phase.screening_metadata_status = SubPhaseStatusChoices.IN_PROGRESS
        selection_phase.current_stage = SelectionStageChoices.SCREENING_OVERVIEW
        selection_phase.save()
        
        messages.success(request, f'Papers distributed successfully! {len(distribution)} researchers assigned with {reviews_per_paper} reviews per paper.')
    
    except Exception as e:
        messages.error(request, f'Distribution failed: {str(e)}')
    
    return redirect('selection:screening_overview', project_id=project_id)


@login_required
@require_http_methods(['POST'])
def screening_bulk_decision(request, project_id):
    """
    Apply bulk decision to all pending screening papers.
    Actions: include_all, exclude_all, send_to_discussion
    """
    project = get_object_or_404(Project, id=project_id)
    
    if request.user != project.owner:
        messages.error(request, 'Only project owner can make bulk decisions')
        return redirect('selection:screening_overview', project_id=project_id)
    
    selection_phase = get_object_or_404(SelectionPhase, project=project)
    action = request.POST.get('action')
    
    if action not in ['include_all', 'exclude_all', 'send_to_discussion']:
        messages.error(request, 'Invalid action')
        return redirect('selection:screening_overview', project_id=project_id)
    
    # Get all screening assignments with pending reviews
    all_assignments = PaperAssignment.objects.filter(
        selection_phase=selection_phase,
        stage=AssignmentStageChoices.SCREENING,
        is_third_reviewer=False
    )
    
    pending_assignments = []
    for assignment in all_assignments:
        review = PaperReview.objects.filter(
            assignment=assignment,
            stage='SCREENING'
        ).first()
        
        if not review or review.decision == SelectionDecisionChoices.PENDING:
            pending_assignments.append(assignment)
    
    count = 0
    if action == 'include_all':
        for assignment in pending_assignments:
            PaperReview.objects.update_or_create(
                assignment=assignment,
                stage='SCREENING',
                defaults={
                    'decision': SelectionDecisionChoices.INCLUDED,
                    'notes': 'Bulk included by owner'
                }
            )
            count += 1
        messages.success(request, f'{count} pending papers marked as INCLUDED')
        
    elif action == 'exclude_all':
        for assignment in pending_assignments:
            PaperReview.objects.update_or_create(
                assignment=assignment,
                stage='SCREENING',
                defaults={
                    'decision': SelectionDecisionChoices.EXCLUDED,
                    'notes': 'Bulk excluded by owner'
                }
            )
            count += 1
        messages.success(request, f'{count} pending papers marked as EXCLUDED')
        
    elif action == 'send_to_discussion':
        selection_phase.current_stage = SelectionStageChoices.SCREENING_DISCUSSION
        selection_phase.save()
        messages.success(request, 'Moved to Screening Discussion phase')
    
    return redirect('selection:screening_overview', project_id=project_id)


@login_required
@require_http_methods(['POST'])
def send_screening_reminder(request, project_id):
    """
    Send reminder notification to a specific researcher for screening.
    """
    project = get_object_or_404(Project, id=project_id)
    
    if request.user != project.owner:
        messages.error(request, 'Only project owner can send reminders')
        return redirect('selection:screening_overview', project_id=project_id)
    
    researcher_id = request.POST.get('researcher_id')
    if not researcher_id:
        messages.error(request, 'No researcher specified')
        return redirect('selection:screening_overview', project_id=project_id)
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        researcher = User.objects.get(id=researcher_id)
        
        from apps.notification.models import Notification
        Notification.objects.create(
            recipient=researcher,
            sender=request.user,
            type='REMINDER',
            title='Screening Review Reminder',
            custom_message=f'You have pending papers to review in the screening phase of project "{project.title}". Please complete your reviews.',
            project=project
        )
        messages.success(request, f'Reminder sent to {researcher.get_full_name() or researcher.username}')
            
    except User.DoesNotExist:
        messages.error(request, 'Researcher not found')
    except Exception as e:
        messages.error(request, f'Failed to send notification: {str(e)}')
    
    return redirect('selection:screening_overview', project_id=project_id)


@login_required
@require_http_methods(['POST'])
def finalize_screening(request, project_id):
    """
    Finalize screening phase and enable fulltext phase.
    Only possible when all reviews are complete and all conflicts are resolved.
    """
    project = get_object_or_404(Project, id=project_id)
    
    if request.user != project.owner:
        messages.error(request, 'Only project owner can finalize screening')
        return redirect('selection:screening_overview', project_id=project_id)
    
    selection_phase = get_object_or_404(SelectionPhase, project=project)
    
    # Check for unresolved conflicts
    discrepancy_service = DiscrepancyResolutionService(selection_phase)
    conflicts = discrepancy_service.get_conflicts(stage='SCREENING')
    
    if conflicts:
        messages.error(request, f'Cannot finalize: {len(conflicts)} unresolved conflicts remain. Go to Discussion to resolve them.')
        return redirect('selection:screening_overview', project_id=project_id)
    
    # Check for pending reviews
    all_assignments = PaperAssignment.objects.filter(
        selection_phase=selection_phase,
        stage=AssignmentStageChoices.SCREENING,
        is_third_reviewer=False
    )
    
    for assignment in all_assignments:
        review = PaperReview.objects.filter(
            assignment=assignment,
            stage='SCREENING'
        ).first()
        if not review or review.decision == SelectionDecisionChoices.PENDING:
            messages.error(request, 'Cannot finalize: Some reviews are still pending.')
            return redirect('selection:screening_overview', project_id=project_id)
    
    # Finalize screening
    selection_phase.screening_metadata_status = SubPhaseStatusChoices.COMPLETED
    selection_phase.discussion_metadata_status = SubPhaseStatusChoices.COMPLETED
    selection_phase.current_stage = SelectionStageChoices.FULLTEXT_OVERVIEW
    selection_phase.save()
    
    messages.success(request, 'Screening phase finalized! Full-text phase is now available.')
    return redirect('selection:fulltext_overview', project_id=project_id)


@login_required
def approved_papers_api(request, project_id):
    """
    API endpoint for Extraction module.
    Returns list of paper IDs approved in fulltext review.
    """
    from apps.selection.services import get_selection_facade
    
    facade = get_selection_facade()
    paper_ids = facade.get_approved_fulltext_papers(project_id)
    
    return JsonResponse({
        'project_id': project_id,
        'approved_paper_ids': paper_ids,
        'count': len(paper_ids)
    })
