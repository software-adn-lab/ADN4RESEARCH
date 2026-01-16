"""
Vistas para resolución de discrepancias.
Responsable de resolver conflictos entre revisores en screening y fulltext.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib import messages

from apps.project.structure.models.project_models import Project
from apps.project.facade import get_project_facade
from apps.selection.features.distribution.models import SelectionPhase
from apps.selection.features.screening.models import PaperAssignment, PaperReview
from apps.selection.features.discussion.models import ConflictResolution
from apps.selection.models.choices import (
    SelectionDecisionChoices,
    AssignmentStageChoices,
    SelectionStageChoices,
)
from apps.selection.features.discussion.services import DiscrepancyResolutionService
from apps.design.api import get_design_protocol


def _get_paper_metadata(selection_phase, paper_ids):
    """Get paper metadata for a list of paper IDs"""
    project_facade = get_project_facade()
    all_studies = project_facade.get_studies_by_project(
        project_id=selection_phase.project_id,
        include_metadata=True
    )
    return {str(s['id']): s for s in all_studies}


def _get_criteria(project_id):
    """Get inclusion/exclusion criteria from design"""
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
    
    return inclusion_criteria, exclusion_criteria


@login_required
def screening_discussion_view(request, project_id):
    """
    Screening Discussion - resolve conflicts from screening phase.
    
    Owner sees ALL conflicts.
    Researchers see only papers where they are assigned as third reviewer.
    """
    project = get_object_or_404(Project, id=project_id)
    selection_phase = get_object_or_404(SelectionPhase, project=project)
    
    is_owner = request.user == project.owner
    discrepancy_service = DiscrepancyResolutionService(selection_phase)
    
    # Get paper metadata
    if is_owner:
        # Owner sees all conflicts
        conflicts = discrepancy_service.get_conflicts(stage='SCREENING')
        third_reviewer_papers = []
    else:
        # Researchers see only their third reviewer assignments
        conflicts = []
        third_reviewer_papers = discrepancy_service.get_user_third_reviewer_assignments(
            request.user, stage='SCREENING'
        )
    
    # Enrich conflicts with paper metadata
    if conflicts or third_reviewer_papers:
        paper_ids = [c['paper_id'] for c in conflicts] + [p['assignment'].paper_id for p in third_reviewer_papers]
        studies_by_id = _get_paper_metadata(selection_phase, paper_ids)
        
        for conflict in conflicts:
            conflict['study'] = studies_by_id.get(conflict['paper_id'], {})
            # Get eligible third reviewers
            conflict['eligible_reviewers'] = discrepancy_service.get_eligible_third_reviewers(
                conflict['paper_id'], stage='SCREENING'
            )
    
    # Get criteria for third reviewer form
    inclusion_criteria, exclusion_criteria = _get_criteria(project_id)
    
    context = {
        'project': project,
        'selection_phase': selection_phase,
        'conflicts': conflicts,
        'third_reviewer_papers': third_reviewer_papers,
        'is_owner': is_owner,
        'current_stage': 'screening_discussion',
        'inclusion_criteria': inclusion_criteria,
        'exclusion_criteria': exclusion_criteria,
    }
    
    return render(request, 'discussion/screening_discussion.html', context)


@login_required
@require_http_methods(['POST'])
def assign_third_reviewer(request, project_id):
    """
    Assign a third reviewer to resolve a screening conflict.
    Only owner can do this.
    """
    project = get_object_or_404(Project, id=project_id)
    
    if request.user != project.owner:
        messages.error(request, 'Only project owner can assign third reviewers')
        return redirect('selection:screening_discussion', project_id=project_id)
    
    selection_phase = get_object_or_404(SelectionPhase, project=project)
    
    paper_id = request.POST.get('paper_id')
    reviewer_id = request.POST.get('reviewer_id')
    
    if not paper_id or not reviewer_id:
        messages.error(request, 'Paper and reviewer are required')
        return redirect('selection:screening_discussion', project_id=project_id)
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        reviewer = User.objects.get(id=reviewer_id)
        discrepancy_service = DiscrepancyResolutionService(selection_phase)
        
        result = discrepancy_service.assign_third_reviewer(
            paper_id=paper_id,
            reviewer=reviewer,
            stage='SCREENING'
        )
        
        # Send notification to third reviewer
        try:
            from apps.notification.models import Notification
            Notification.objects.create(
                recipient=reviewer,
                sender=request.user,
                type='ASSIGNMENT',
                title='Third Reviewer Assignment',
                custom_message=f'You have been assigned as a third reviewer to resolve a conflict in project "{project.title}".',
                project=project
            )
        except Exception:
            pass  # Don't fail if notification fails
        
        messages.success(request, f'Third reviewer {reviewer.get_full_name() or reviewer.username} assigned successfully')
        
    except User.DoesNotExist:
        messages.error(request, 'Reviewer not found')
    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f'Failed to assign third reviewer: {str(e)}')
    
    return redirect('selection:screening_discussion', project_id=project_id)


@login_required
@require_http_methods(['POST'])
def owner_vote(request, project_id):
    """
    Owner resolves a conflict with their final vote.
    """
    project = get_object_or_404(Project, id=project_id)
    
    if request.user != project.owner:
        messages.error(request, 'Only project owner can make final vote')
        return redirect('selection:screening_discussion', project_id=project_id)
    
    selection_phase = get_object_or_404(SelectionPhase, project=project)
    
    paper_id = request.POST.get('paper_id')
    decision = request.POST.get('decision')
    notes = request.POST.get('notes', '')
    
    if not paper_id or decision not in ['INCLUDED', 'EXCLUDED']:
        messages.error(request, 'Paper and valid decision are required')
        return redirect('selection:screening_discussion', project_id=project_id)
    
    try:
        discrepancy_service = DiscrepancyResolutionService(selection_phase)
        discrepancy_service.resolve_with_owner_vote(
            paper_id=paper_id,
            owner=request.user,
            decision=decision,
            notes=notes,
            stage='SCREENING'
        )
        
        messages.success(request, f'Conflict resolved with {decision}')
        
    except Exception as e:
        messages.error(request, f'Failed to resolve conflict: {str(e)}')
    
    return redirect('selection:screening_discussion', project_id=project_id)


@login_required
@require_http_methods(['POST'])
def third_reviewer_submit(request, project_id):
    """
    Third reviewer submits their decision.
    """
    project = get_object_or_404(Project, id=project_id)
    selection_phase = get_object_or_404(SelectionPhase, project=project)
    
    assignment_id = request.POST.get('assignment_id')
    decision = request.POST.get('decision')
    notes = request.POST.get('notes', '')
    criterion_id = request.POST.get('criterion_id')
    criterion_label = request.POST.get('criterion_label')
    
    if not assignment_id or decision not in ['INCLUDED', 'EXCLUDED']:
        messages.error(request, 'Assignment and valid decision are required')
        return redirect('selection:screening_discussion', project_id=project_id)
    
    try:
        assignment = PaperAssignment.objects.get(
            id=assignment_id,
            selection_phase=selection_phase,
            researcher=request.user,
            is_third_reviewer=True
        )
        
        discrepancy_service = DiscrepancyResolutionService(selection_phase)
        discrepancy_service.process_third_reviewer_decision(
            assignment=assignment,
            decision=decision,
            notes=notes,
            criterion_id=criterion_id,
            criterion_label=criterion_label
        )
        
        messages.success(request, 'Your decision has been submitted and the conflict is resolved')
        
    except PaperAssignment.DoesNotExist:
        messages.error(request, 'Assignment not found or you are not the third reviewer')
    except Exception as e:
        messages.error(request, f'Failed to submit decision: {str(e)}')
    
    return redirect('selection:screening_discussion', project_id=project_id)


# ============================================
# FULLTEXT DISCUSSION VIEWS
# ============================================

@login_required
def fulltext_discussion_view(request, project_id):
    """
    Fulltext Discussion - resolve conflicts from fulltext review phase.
    
    Owner sees ALL conflicts.
    Researchers see only papers where they are assigned as third reviewer.
    """
    project = get_object_or_404(Project, id=project_id)
    selection_phase = get_object_or_404(SelectionPhase, project=project)
    
    # Check if fulltext phase is accessible
    if not selection_phase.can_access_fulltext():
        messages.error(request, 'Fulltext phase is not yet available. Complete screening first.')
        return redirect('selection:screening_overview', project_id=project_id)
    
    is_owner = request.user == project.owner
    discrepancy_service = DiscrepancyResolutionService(selection_phase)
    
    if is_owner:
        conflicts = discrepancy_service.get_conflicts(stage='FULL_TEXT')
        third_reviewer_papers = []
    else:
        conflicts = []
        third_reviewer_papers = discrepancy_service.get_user_third_reviewer_assignments(
            request.user, stage='FULL_TEXT'
        )
    
    # Enrich with metadata
    if conflicts or third_reviewer_papers:
        paper_ids = [c['paper_id'] for c in conflicts] + [p['assignment'].paper_id for p in third_reviewer_papers]
        studies_by_id = _get_paper_metadata(selection_phase, paper_ids)
        
        for conflict in conflicts:
            conflict['study'] = studies_by_id.get(conflict['paper_id'], {})
            conflict['eligible_reviewers'] = discrepancy_service.get_eligible_third_reviewers(
                conflict['paper_id'], stage='FULL_TEXT'
            )
    
    inclusion_criteria, exclusion_criteria = _get_criteria(project_id)
    
    context = {
        'project': project,
        'selection_phase': selection_phase,
        'conflicts': conflicts,
        'third_reviewer_papers': third_reviewer_papers,
        'is_owner': is_owner,
        'current_stage': 'fulltext_discussion',
        'inclusion_criteria': inclusion_criteria,
        'exclusion_criteria': exclusion_criteria,
    }
    
    return render(request, 'discussion/fulltext_discussion.html', context)


@login_required
@require_http_methods(['POST'])
def assign_fulltext_third_reviewer(request, project_id):
    """
    Assign a third reviewer for fulltext conflict.
    """
    project = get_object_or_404(Project, id=project_id)
    
    if request.user != project.owner:
        messages.error(request, 'Only project owner can assign third reviewers')
        return redirect('selection:fulltext_discussion', project_id=project_id)
    
    selection_phase = get_object_or_404(SelectionPhase, project=project)
    
    paper_id = request.POST.get('paper_id')
    reviewer_id = request.POST.get('reviewer_id')
    
    if not paper_id or not reviewer_id:
        messages.error(request, 'Paper and reviewer are required')
        return redirect('selection:fulltext_discussion', project_id=project_id)
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        reviewer = User.objects.get(id=reviewer_id)
        discrepancy_service = DiscrepancyResolutionService(selection_phase)
        
        discrepancy_service.assign_third_reviewer(
            paper_id=paper_id,
            reviewer=reviewer,
            stage='FULL_TEXT'
        )
        
        try:
            from apps.notification.models import Notification
            Notification.objects.create(
                recipient=reviewer,
                sender=request.user,
                type='ASSIGNMENT',
                title='Third Reviewer Assignment (Full-text)',
                custom_message=f'You have been assigned as a third reviewer to resolve a full-text conflict in project "{project.title}".',
                project=project
            )
        except Exception:
            pass
        
        messages.success(request, f'Third reviewer {reviewer.get_full_name() or reviewer.username} assigned successfully')
        
    except User.DoesNotExist:
        messages.error(request, 'Reviewer not found')
    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f'Failed to assign third reviewer: {str(e)}')
    
    return redirect('selection:fulltext_discussion', project_id=project_id)


@login_required
@require_http_methods(['POST'])
def fulltext_owner_vote(request, project_id):
    """
    Owner resolves a fulltext conflict with their final vote.
    """
    project = get_object_or_404(Project, id=project_id)
    
    if request.user != project.owner:
        messages.error(request, 'Only project owner can make final vote')
        return redirect('selection:fulltext_discussion', project_id=project_id)
    
    selection_phase = get_object_or_404(SelectionPhase, project=project)
    
    paper_id = request.POST.get('paper_id')
    decision = request.POST.get('decision')
    notes = request.POST.get('notes', '')
    
    if not paper_id or decision not in ['INCLUDED', 'EXCLUDED']:
        messages.error(request, 'Paper and valid decision are required')
        return redirect('selection:fulltext_discussion', project_id=project_id)
    
    try:
        discrepancy_service = DiscrepancyResolutionService(selection_phase)
        discrepancy_service.resolve_with_owner_vote(
            paper_id=paper_id,
            owner=request.user,
            decision=decision,
            notes=notes,
            stage='FULL_TEXT'
        )
        
        messages.success(request, f'Conflict resolved with {decision}')
        
    except Exception as e:
        messages.error(request, f'Failed to resolve conflict: {str(e)}')
    
    return redirect('selection:fulltext_discussion', project_id=project_id)


@login_required
@require_http_methods(['POST'])
def fulltext_third_reviewer_submit(request, project_id):
    """
    Third reviewer submits their fulltext decision.
    """
    project = get_object_or_404(Project, id=project_id)
    selection_phase = get_object_or_404(SelectionPhase, project=project)
    
    assignment_id = request.POST.get('assignment_id')
    decision = request.POST.get('decision')
    notes = request.POST.get('notes', '')
    criterion_id = request.POST.get('criterion_id')
    criterion_label = request.POST.get('criterion_label')
    
    if not assignment_id or decision not in ['INCLUDED', 'EXCLUDED']:
        messages.error(request, 'Assignment and valid decision are required')
        return redirect('selection:fulltext_discussion', project_id=project_id)
    
    try:
        assignment = PaperAssignment.objects.get(
            id=assignment_id,
            selection_phase=selection_phase,
            researcher=request.user,
            is_third_reviewer=True,
            stage=AssignmentStageChoices.FULLTEXT
        )
        
        discrepancy_service = DiscrepancyResolutionService(selection_phase)
        discrepancy_service.process_third_reviewer_decision(
            assignment=assignment,
            decision=decision,
            notes=notes,
            criterion_id=criterion_id,
            criterion_label=criterion_label
        )
        
        messages.success(request, 'Your decision has been submitted and the conflict is resolved')
        
    except PaperAssignment.DoesNotExist:
        messages.error(request, 'Assignment not found or you are not the third reviewer')
    except Exception as e:
        messages.error(request, f'Failed to submit decision: {str(e)}')
    
    return redirect('selection:fulltext_discussion', project_id=project_id)
