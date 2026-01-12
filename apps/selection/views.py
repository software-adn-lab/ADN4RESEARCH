from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.project.facade import get_project_facade
from apps.design.api import get_design_protocol
from apps.project.structure.models.project_models import Project, Membership
from .models import (
    SelectionPhase, PaperAssignment, PaperReview,
    SelectionStageChoices, SelectionDecisionChoices
)
from .services import PaperDistributionService


@login_required
def selection_overview(request, project_id):
    """
    Overview page - shows distribution progress and team status.
    
    Corresponds to the first image: "Selection - Overview"
    """
    project = get_object_or_404(Project, id=project_id)
    
    # Get or create selection phase
    selection_phase, created = SelectionPhase.objects.get_or_create(
        project=project,
        defaults={'status': 'ON_GOING', 'current_stage': SelectionStageChoices.OVERVIEW}
    )
    
    # Check if user is owner
    is_owner = request.user == project.owner
    
    # Get current user's progress
    user_assignments = PaperAssignment.objects.filter(
        selection_phase=selection_phase,
        researcher=request.user
    )
    
    user_total = user_assignments.count()
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
        # Ensure percentages sum to 100 by calculating excluded as remainder
        user_excluded_pct = 100 - user_pending_pct - user_included_pct
    else:
        user_pending_pct = 0
        user_included_pct = 0
        user_excluded_pct = 0
    
    # Get team progress (excluding current user)
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
            # Ensure percentages sum to 100 by calculating excluded as remainder
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
    
    return render(request, 'selection/overview.html', context)


@login_required
@require_http_methods(['POST'])
def distribute_papers(request, project_id):
    """
    Execute paper distribution algorithm.
    
    Called from overview page when owner clicks "Distribute Papers"
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


@login_required
def screening_view(request, project_id):
    """
    Screening page - abstract-based paper review.
    
    Corresponds to the third image: "Selection - Screening"
    """
    project = get_object_or_404(Project, id=project_id)
    selection_phase = get_object_or_404(SelectionPhase, project=project)
    
    # Get papers assigned to this user
    assignments = PaperAssignment.objects.filter(
        selection_phase=selection_phase,
        researcher=request.user
    )
    
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
                # Convert ID to string to ensure consistency (design API returns ints, custom criteria use strings)
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
                
                # Get existing review if any
                review = PaperReview.objects.filter(
                    assignment=assignment,
                    stage=SelectionStageChoices.SCREENING
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
    
    return render(request, 'selection/screening.html', context)


@login_required
@require_http_methods(['POST'])
def submit_review(request, project_id, assignment_id):
    """
    Submit a review decision for a paper.
    Notes can be saved even if decision is not changed (defaults to previous or PENDING).
    """
    assignment = get_object_or_404(PaperAssignment, id=assignment_id)
    
    # Verify user owns this assignment
    if assignment.researcher != request.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    stage = request.POST.get('stage', SelectionStageChoices.SCREENING)
    notes = request.POST.get('notes', '')
    criterion_id = request.POST.get('criterion_id') or None
    criterion_label = request.POST.get('criterion_label') or None
    decision_from_request = request.POST.get('decision')
    
    existing_review = PaperReview.objects.filter(
        assignment=assignment,
        stage=stage
    ).first()
    previous_decision = existing_review.decision if existing_review else SelectionDecisionChoices.PENDING
    
    decision = decision_from_request or previous_decision or SelectionDecisionChoices.PENDING
    
    # If decision is include/exclude, criterion is required
    if decision in [SelectionDecisionChoices.INCLUDED, SelectionDecisionChoices.EXCLUDED] and not criterion_id:
        return JsonResponse({'error': 'Criterion is required for this decision'}, status=400)
    
    review, created = PaperReview.objects.update_or_create(
        assignment=assignment,
        stage=stage,
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


@login_required
def fulltext_view(request, project_id):
    """
    Full-text screening page.
    
    Corresponds to the fourth image: "Selection - Full-text"
    """
    project = get_object_or_404(Project, id=project_id)
    selection_phase = get_object_or_404(SelectionPhase, project=project)
    
    # Similar to screening but for full-text stage
    context = {
        'project': project,
        'selection_phase': selection_phase,
        'current_stage': 'fulltext'
    }
    
    return render(request, 'selection/fulltext.html', context)


@login_required
def discussion_view(request, project_id):
    """
    Discussion page - conflict resolution.
    
    Corresponds to the fifth image: "Selection - Discussion"
    """
    project = get_object_or_404(Project, id=project_id)
    selection_phase = get_object_or_404(SelectionPhase, project=project)
    
    # Find papers with conflicts (different decisions from different researchers)
    from django.db.models import Count
    
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
    
    return render(request, 'selection/discussion.html', context)
