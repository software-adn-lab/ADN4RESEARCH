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
from django.db.models import Max
from django.utils.dateparse import parse_date
from datetime import datetime, time

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


def _get_pending_all_paper_ids(selection_phase):
    """
    Return paper_ids where all reviewers are still pending (no include/exclude yet).
    """
    assignments = PaperAssignment.objects.filter(
        selection_phase=selection_phase,
        stage=AssignmentStageChoices.SCREENING,
        is_third_reviewer=False
    )
    paper_ids = assignments.values_list('paper_id', flat=True).distinct()
    pending_all = []

    for paper_id in paper_ids:
        reviews = PaperReview.objects.filter(
            assignment__selection_phase=selection_phase,
            assignment__paper_id=paper_id,
            assignment__stage=AssignmentStageChoices.SCREENING,
            assignment__is_third_reviewer=False,
            stage='SCREENING'
        )
        has_decision = reviews.exclude(decision=SelectionDecisionChoices.PENDING).exists()
        if not has_decision:
            pending_all.append(paper_id)

    return pending_all


def _get_design_end_date(project):
    """
    Return the last planned end date for the design phase.

    Preference order:
    1) Max planned_end_date from DesignStagePlan
    2) DesignPhase.end_date
    """
    design_end_date = None

    try:
        from apps.design.design_phase_logic.models.design_phase import DesignStagePlan

        plan_end = (
            DesignStagePlan.objects.filter(phase_id=project.id)
            .aggregate(max_end=Max('planned_end_date'))
            .get('max_end')
        )
        if plan_end:
            design_end_date = plan_end
    except Exception:
        # If design schedule isn't available, fall back to phase end date
        pass

    try:
        from apps.design.design_phase_logic.models.design_phase import DesignPhase

        phase = DesignPhase.objects.get(pk=project.id)
        if phase.end_date:
            phase_end = phase.end_date.date()
            if not design_end_date or phase_end > design_end_date:
                design_end_date = phase_end
    except Exception:
        pass

    return design_end_date


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
    elif selection_phase.screening_metadata_end_date and now > selection_phase.screening_metadata_end_date:
        phase_mode = 'finalizado'
    else:
        phase_mode = 'en_curso'

    schedule_configured = selection_phase.is_selection_schedule_configured()
    screening_locked = not schedule_configured or not selection_phase.is_screening_window_open(now=now)

    design_end_date = _get_design_end_date(project)
    schedule_min_date = design_end_date or project.created_at.date()
    
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

    pending_all_paper_ids = _get_pending_all_paper_ids(selection_phase)
    pending_all_count = len(pending_all_paper_ids)

    if (
        selection_phase.screening_status == SubPhaseStatusChoices.COMPLETED and
        conflicts_count == 0 and
        pending_all_count == 0 and
        selection_phase.discussion_metadata_status != SubPhaseStatusChoices.COMPLETED
    ):
        selection_phase.discussion_metadata_status = SubPhaseStatusChoices.COMPLETED
        selection_phase.current_stage = SelectionStageChoices.FULLTEXT_OVERVIEW
        selection_phase.save(update_fields=['discussion_metadata_status', 'current_stage'])
    
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
        'can_finalize': selection_phase.screening_distributed and selection_phase.screening_status != SubPhaseStatusChoices.COMPLETED,
        'pending_all_count': pending_all_count,
        'schedule_configured': schedule_configured,
        'screening_locked': screening_locked,
        'screening_start_date': selection_phase.screening_metadata_start_date,
        'screening_end_date': selection_phase.screening_metadata_end_date,
        'fulltext_start_date': selection_phase.fulltext_screening_start_date,
        'fulltext_end_date': selection_phase.fulltext_screening_end_date,
        'show_schedule_modal': bool(request.GET.get('schedule')) or (is_owner and not schedule_configured),
        'design_end_date': design_end_date,
        'schedule_min_date': schedule_min_date,
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

    if not selection_phase.is_selection_schedule_configured():
        messages.error(request, 'Configure screening/full-text dates before distributing papers.')
        return redirect('selection:screening_overview', project_id=project_id)
    if not selection_phase.is_screening_window_open():
        start_date = selection_phase.screening_metadata_start_date
        start_label = start_date.date() if start_date else 'scheduled date'
        messages.error(request, f'Screening starts on {start_label}. You cannot distribute yet.')
        return redirect('selection:screening_overview', project_id=project_id)
    
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
def configure_selection_schedule(request, project_id):
    """
    Configure screening and full-text schedule dates for selection phase.
    """
    project = get_object_or_404(Project, id=project_id)

    if request.user != project.owner:
        messages.error(request, 'Only project owner can configure selection dates')
        return redirect('selection:screening_overview', project_id=project_id)

    selection_phase, _ = SelectionPhase.objects.get_or_create(
        project=project,
        defaults={
            'status': 'ON_GOING',
            'current_stage': SelectionStageChoices.SCREENING_OVERVIEW
        }
    )

    screening_start_str = request.POST.get('screening_start_date')
    screening_end_str = request.POST.get('screening_end_date')
    fulltext_start_str = request.POST.get('fulltext_start_date')
    fulltext_end_str = request.POST.get('fulltext_end_date')

    if not all([screening_start_str, screening_end_str, fulltext_start_str, fulltext_end_str]):
        messages.error(request, 'All screening and full-text dates are required.')
        return redirect('selection:screening_overview', project_id=project_id)

    screening_start = parse_date(screening_start_str)
    screening_end = parse_date(screening_end_str)
    fulltext_start = parse_date(fulltext_start_str)
    fulltext_end = parse_date(fulltext_end_str)

    if not all([screening_start, screening_end, fulltext_start, fulltext_end]):
        messages.error(request, 'Invalid date format.')
        return redirect('selection:screening_overview', project_id=project_id)

    if screening_start >= screening_end:
        messages.error(request, 'Screening start date must be before end date.')
        return redirect('selection:screening_overview', project_id=project_id)

    if fulltext_start >= fulltext_end:
        messages.error(request, 'Full-text start date must be before end date.')
        return redirect('selection:screening_overview', project_id=project_id)

    if fulltext_start < screening_end:
        messages.error(request, 'Full-text must start on or after screening end date.')
        return redirect('selection:screening_overview', project_id=project_id)

    design_end_date = _get_design_end_date(project)
    if design_end_date and screening_start < design_end_date:
        messages.error(
            request,
            f'Selection cannot start before design ends ({design_end_date}).'
        )
        return redirect('selection:screening_overview', project_id=project_id)

    project_start = project.created_at.date()
    project_end = project.end_date.date() if project.end_date else None

    for label, date_value in [
        ('Screening start', screening_start),
        ('Screening end', screening_end),
        ('Full-text start', fulltext_start),
        ('Full-text end', fulltext_end),
    ]:
        if date_value < project_start:
            messages.error(request, f'{label} cannot be before project start ({project_start}).')
            return redirect('selection:screening_overview', project_id=project_id)
        if project_end and date_value > project_end:
            messages.error(request, f'{label} cannot be after project end ({project_end}).')
            return redirect('selection:screening_overview', project_id=project_id)

    tz = timezone.get_current_timezone()
    screening_start_dt = timezone.make_aware(datetime.combine(screening_start, time.min), tz)
    screening_end_dt = timezone.make_aware(datetime.combine(screening_end, time.max), tz)
    fulltext_start_dt = timezone.make_aware(datetime.combine(fulltext_start, time.min), tz)
    fulltext_end_dt = timezone.make_aware(datetime.combine(fulltext_end, time.max), tz)

    selection_phase.screening_metadata_start_date = screening_start_dt
    selection_phase.screening_metadata_end_date = screening_end_dt
    selection_phase.fulltext_screening_start_date = fulltext_start_dt
    selection_phase.fulltext_screening_end_date = fulltext_end_dt
    selection_phase.save(update_fields=[
        'screening_metadata_start_date',
        'screening_metadata_end_date',
        'fulltext_screening_start_date',
        'fulltext_screening_end_date',
    ])

    messages.success(request, 'Selection schedule saved successfully.')
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
    if not selection_phase.is_selection_schedule_configured():
        messages.warning(request, 'Configure screening/full-text dates before applying bulk decisions.')
        return redirect('selection:screening_overview', project_id=project_id)
    action = request.POST.get('action')

    if selection_phase.screening_metadata_status != SubPhaseStatusChoices.COMPLETED:
        messages.warning(request, 'Finalize screening before applying bulk decisions.')
        return redirect('selection:screening_overview', project_id=project_id)

    if not selection_phase.is_screening_window_open():
        start_date = selection_phase.screening_metadata_start_date
        start_label = start_date.date() if start_date else 'scheduled date'
        messages.warning(request, f'Screening starts on {start_label}.')
        return redirect('selection:screening_overview', project_id=project_id)
    
    if action not in ['include_all', 'exclude_all', 'send_to_discussion']:
        messages.error(request, 'Invalid action')
        return redirect('selection:screening_overview', project_id=project_id)
    
    pending_all_paper_ids = _get_pending_all_paper_ids(selection_phase)
    if not pending_all_paper_ids:
        messages.warning(request, 'No papers pending for all reviewers.')
        return redirect('selection:screening_overview', project_id=project_id)

    pending_assignments = PaperAssignment.objects.filter(
        selection_phase=selection_phase,
        stage=AssignmentStageChoices.SCREENING,
        is_third_reviewer=False,
        paper_id__in=pending_all_paper_ids
    )

    count = len(pending_all_paper_ids)
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
        messages.success(request, f'{count} pending papers marked as EXCLUDED')
        
    elif action == 'send_to_discussion':
        selection_phase.current_stage = SelectionStageChoices.SCREENING_DISCUSSION
        selection_phase.save()
        messages.success(request, f'{count} pending papers sent to discussion')

    if action in ['include_all', 'exclude_all']:
        discrepancy_service = DiscrepancyResolutionService(selection_phase)
        conflicts = discrepancy_service.get_conflicts(stage='SCREENING')
        pending_all_remaining = _get_pending_all_paper_ids(selection_phase)
        if (
            selection_phase.screening_metadata_status == SubPhaseStatusChoices.COMPLETED and
            not conflicts and
            not pending_all_remaining
        ):
            selection_phase.discussion_metadata_status = SubPhaseStatusChoices.COMPLETED
            selection_phase.current_stage = SelectionStageChoices.FULLTEXT_OVERVIEW
            selection_phase.save(update_fields=['discussion_metadata_status', 'current_stage'])
            messages.success(request, 'Screening ready. Full-text phase is now available.')
            return redirect('selection:fulltext_overview', project_id=project_id)
    
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
    Owner can finalize at any time. Full-text becomes available only when
    pending-all papers are decided and discussions are resolved.
    """
    project = get_object_or_404(Project, id=project_id)
    
    if request.user != project.owner:
        messages.error(request, 'Only project owner can finalize screening')
        return redirect('selection:screening_overview', project_id=project_id)
    
    selection_phase = get_object_or_404(SelectionPhase, project=project)
    if not selection_phase.is_selection_schedule_configured():
        messages.error(request, 'Configure screening/full-text dates before finalizing screening.')
        return redirect('selection:screening_overview', project_id=project_id)

    if not selection_phase.is_screening_window_open():
        start_date = selection_phase.screening_metadata_start_date
        start_label = start_date.date() if start_date else 'scheduled date'
        messages.error(request, f'Screening starts on {start_label}.')
        return redirect('selection:screening_overview', project_id=project_id)
    
    discrepancy_service = DiscrepancyResolutionService(selection_phase)
    conflicts = discrepancy_service.get_conflicts(stage='SCREENING')
    pending_all_paper_ids = _get_pending_all_paper_ids(selection_phase)

    # Finalize screening reviews
    now = timezone.now()
    selection_phase.screening_metadata_status = SubPhaseStatusChoices.COMPLETED
    selection_phase.screening_metadata_end_date = now
    if selection_phase.fulltext_screening_status == SubPhaseStatusChoices.NOT_STARTED:
        selection_phase.fulltext_screening_start_date = now
    selection_phase.save(update_fields=[
        'screening_metadata_status',
        'screening_metadata_end_date',
        'fulltext_screening_start_date',
    ])

    if not conflicts and not pending_all_paper_ids:
        selection_phase.discussion_metadata_status = SubPhaseStatusChoices.COMPLETED
        selection_phase.current_stage = SelectionStageChoices.FULLTEXT_OVERVIEW
        selection_phase.save(update_fields=['discussion_metadata_status', 'current_stage'])
        messages.success(request, 'Screening finalized! Full-text phase is now available.')
        return redirect('selection:fulltext_overview', project_id=project_id)

    messages.warning(
        request,
        'Screening finalized. Resolve discussions and decide pending papers before moving to full-text.'
    )
    return redirect('selection:screening_overview', project_id=project_id)


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
