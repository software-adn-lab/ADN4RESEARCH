import logging
from typing import List

from apps.project.structure.models.project_models import Membership

logger = logging.getLogger(__name__)


class DiscrepancyResolutionService:
    """
    Service for managing discrepancies/conflicts in paper reviews.

    Handles:
    - Detecting conflicts (different decisions from reviewers)
    - Assigning third reviewers
    - Recording owner votes
    - Tracking resolution status
    """

    def __init__(self, selection_phase):
        self.selection_phase = selection_phase

    def get_conflicts(self, stage: str, include_resolved: bool = False) -> List[dict]:
        """
        Get conflicts for a given stage.

        Args:
            stage: 'SCREENING' or 'FULL_TEXT'
            include_resolved: If True, include resolved conflicts in result

        Returns:
            List of conflict dicts with paper info and reviews
        """
        from apps.selection.domain.models import PaperAssignment, PaperReview
        from apps.selection.domain.models import ConflictResolution
        from apps.selection.domain.choices import SelectionDecisionChoices, AssignmentStageChoices

        # Map stage to assignment stage
        assignment_stage = AssignmentStageChoices.SCREENING if stage == 'SCREENING' else AssignmentStageChoices.FULLTEXT
        review_stage = 'SCREENING' if stage == 'SCREENING' else 'FULL_TEXT'

        conflicts = []

        # Base papers: regular reviewer assignments.
        base_paper_ids = set(PaperAssignment.objects.filter(
            selection_phase=self.selection_phase,
            stage=assignment_stage,
            is_third_reviewer=False
        ).values_list('paper_id', flat=True).distinct())

        # Also include papers that already have a conflict record.
        conflict_paper_ids = set(ConflictResolution.objects.filter(
            selection_phase=self.selection_phase,
            stage=assignment_stage,
        ).values_list('paper_id', flat=True))

        paper_ids = sorted(base_paper_ids | conflict_paper_ids)

        for paper_id in paper_ids:
            # Existing conflict metadata (if any)
            existing_resolution = ConflictResolution.objects.filter(
                selection_phase=self.selection_phase,
                paper_id=paper_id,
                stage=assignment_stage
            ).select_related('third_reviewer', 'resolved_by').first()

            # Reviews from initial reviewers (exclude pending).
            reviews = PaperReview.objects.filter(
                assignment__selection_phase=self.selection_phase,
                assignment__paper_id=paper_id,
                assignment__stage=assignment_stage,
                assignment__is_third_reviewer=False,
                stage=review_stage
            ).exclude(decision=SelectionDecisionChoices.PENDING).select_related('assignment__researcher')

            decisions = set(reviews.values_list('decision', flat=True))
            has_disagreement = len(decisions) > 1
            has_resolution_record = existing_resolution is not None

            # Not a conflict candidate at all.
            if not has_disagreement and not has_resolution_record:
                continue

            is_resolved = bool(existing_resolution and existing_resolution.is_resolved)
            if is_resolved and not include_resolved:
                continue

            # Third-reviewer assignment (if any).
            third_assignment = PaperAssignment.objects.filter(
                selection_phase=self.selection_phase,
                paper_id=paper_id,
                stage=assignment_stage,
                is_third_reviewer=True,
            ).select_related('researcher').order_by('-assigned_at', '-id').first()

            third_review = None
            if third_assignment:
                third_review = PaperReview.objects.filter(
                    assignment=third_assignment,
                    stage=review_stage
                ).order_by('-reviewed_at', '-id').first()

            third_reviewer_pending = bool(
                third_assignment and
                (not third_review or third_review.decision == SelectionDecisionChoices.PENDING) and
                not is_resolved
            )

            status = 'PENDING'
            if is_resolved:
                status = 'RESOLVED'
            elif third_assignment:
                status = 'ASSIGNED'

            conflict_data = {
                'paper_id': paper_id,
                'reviews': list(reviews),
                'decisions': list(decisions),
                'resolution': existing_resolution,
                'reviewers': [r.assignment.researcher for r in reviews],
                'is_resolved': is_resolved,
                'resolution_method': existing_resolution.resolution_method if existing_resolution else None,
                'final_decision': existing_resolution.final_decision if existing_resolution else None,
                'resolved_at': existing_resolution.resolved_at if existing_resolution else None,
                'resolved_by': existing_resolution.resolved_by if existing_resolution else None,
                'third_reviewer': (
                    existing_resolution.third_reviewer
                    if existing_resolution and existing_resolution.third_reviewer_id
                    else (third_assignment.researcher if third_assignment else None)
                ),
                'third_assignment': third_assignment,
                'third_review': third_review,
                'has_third_assignment': bool(third_assignment),
                'third_reviewer_pending': third_reviewer_pending,
                'has_disagreement': has_disagreement,
                'status': status,
            }
            conflicts.append(conflict_data)

        # Show active items first, resolved at the bottom.
        status_order = {'PENDING': 0, 'ASSIGNED': 1, 'RESOLVED': 2}
        conflicts.sort(key=lambda c: (status_order.get(c['status'], 99), str(c['paper_id'])))

        return conflicts

    def get_user_third_reviewer_assignments(self, user, stage: str) -> List[dict]:
        """
        Get papers where user is assigned as third reviewer.

        Args:
            user: User object
            stage: 'SCREENING' or 'FULL_TEXT'

        Returns:
            List of assignment dicts for third reviewer papers
        """
        from apps.selection.domain.models import PaperAssignment, PaperReview
        from apps.selection.domain.models import ConflictResolution
        from apps.selection.domain.choices import AssignmentStageChoices
        from apps.project.facade import get_project_facade

        assignment_stage = AssignmentStageChoices.SCREENING if stage == 'SCREENING' else AssignmentStageChoices.FULLTEXT
        review_stage = 'SCREENING' if stage == 'SCREENING' else 'FULL_TEXT'

        # Get third reviewer assignments for this user
        third_reviewer_assignments = PaperAssignment.objects.filter(
            selection_phase=self.selection_phase,
            researcher=user,
            stage=assignment_stage,
            is_third_reviewer=True
        )

        if not third_reviewer_assignments.exists():
            return []

        project_facade = get_project_facade()
        all_studies = project_facade.get_studies_by_project(
            project_id=self.selection_phase.project_id,
            include_metadata=True
        )
        studies_by_id = {str(s['id']): s for s in all_studies}

        result = []
        for assignment in third_reviewer_assignments:
            # Get the conflict resolution record
            conflict = ConflictResolution.objects.filter(
                selection_phase=self.selection_phase,
                paper_id=assignment.paper_id,
                stage=assignment_stage
            ).first()

            # Get original reviews
            original_reviews = PaperReview.objects.filter(
                assignment__selection_phase=self.selection_phase,
                assignment__paper_id=assignment.paper_id,
                assignment__stage=assignment_stage,
                assignment__is_third_reviewer=False,
                stage=review_stage
            ).select_related('assignment__researcher')

            # Get third reviewer's own review
            own_review = PaperReview.objects.filter(
                assignment=assignment,
                stage=review_stage
            ).first()

            study = studies_by_id.get(assignment.paper_id, {})

            result.append({
                'assignment': assignment,
                'study': study,
                'conflict': conflict,
                'original_reviews': list(original_reviews),
                'own_review': own_review,
                'is_resolved': conflict.is_resolved if conflict else False
            })

        return result

    def assign_third_reviewer(self, paper_id: str, reviewer, stage: str) -> dict:
        """
        Assign a third reviewer to resolve a conflict.

        Args:
            paper_id: Paper UUID
            reviewer: User object for third reviewer
            stage: 'SCREENING' or 'FULL_TEXT'

        Returns:
            Dict with assignment and conflict resolution info
        """
        from apps.selection.domain.models import PaperAssignment
        from apps.selection.domain.models import ConflictResolution
        from apps.selection.domain.choices import AssignmentStageChoices, ResolutionMethodChoices

        assignment_stage = AssignmentStageChoices.SCREENING if stage == 'SCREENING' else AssignmentStageChoices.FULLTEXT

        # Owner should resolve via final vote, not as third reviewer.
        if reviewer.id == self.selection_phase.project.owner_id:
            raise ValueError("Project owner cannot be assigned as third reviewer. Use owner final decision.")

        # Prevent multiple simultaneous third-reviewer assignments.
        existing_third_assignment = PaperAssignment.objects.filter(
            selection_phase=self.selection_phase,
            paper_id=paper_id,
            stage=assignment_stage,
            is_third_reviewer=True
        ).exists()
        if existing_third_assignment:
            raise ValueError(
                "A third reviewer is already assigned to this paper. "
                "Send a reminder, cancel assignment, or use owner final decision."
            )

        existing_conflict = ConflictResolution.objects.filter(
            selection_phase=self.selection_phase,
            paper_id=paper_id,
            stage=assignment_stage
        ).first()
        if existing_conflict and existing_conflict.is_resolved:
            raise ValueError("This conflict is already resolved.")

        # Verify reviewer hasn't reviewed this paper already
        existing_assignment = PaperAssignment.objects.filter(
            selection_phase=self.selection_phase,
            paper_id=paper_id,
            researcher=reviewer,
            stage=assignment_stage
        ).exists()

        if existing_assignment:
            raise ValueError("This researcher has already reviewed this paper")

        # Create or update conflict resolution
        conflict, created = ConflictResolution.objects.update_or_create(
            selection_phase=self.selection_phase,
            paper_id=paper_id,
            stage=assignment_stage,
            defaults={
                'resolution_method': ResolutionMethodChoices.THIRD_REVIEWER,
                'third_reviewer': reviewer,
                'is_resolved': False,
                'final_decision': None,
                'resolved_by': None,
                'resolved_at': None,
            }
        )

        # Create assignment for third reviewer
        assignment = PaperAssignment.objects.create(
            selection_phase=self.selection_phase,
            paper_id=paper_id,
            researcher=reviewer,
            stage=assignment_stage,
            is_third_reviewer=True
        )

        logger.info(f"[DISCREPANCY] Assigned third reviewer {reviewer.username} for paper {paper_id[:8]}")

        return {
            'assignment': assignment,
            'conflict': conflict
        }

    def cancel_third_reviewer_assignment(self, paper_id: str, stage: str):
        """
        Cancel current third-reviewer assignment for an unresolved conflict.
        """
        from apps.selection.domain.models import PaperAssignment, PaperReview, ConflictResolution
        from apps.selection.domain.choices import AssignmentStageChoices, ResolutionMethodChoices

        assignment_stage = AssignmentStageChoices.SCREENING if stage == 'SCREENING' else AssignmentStageChoices.FULLTEXT
        review_stage = 'SCREENING' if stage == 'SCREENING' else 'FULL_TEXT'

        conflict = ConflictResolution.objects.filter(
            selection_phase=self.selection_phase,
            paper_id=paper_id,
            stage=assignment_stage
        ).first()
        if not conflict:
            raise ValueError("No conflict record found for this paper.")
        if conflict.is_resolved:
            raise ValueError("Conflict is already resolved; third reviewer assignment cannot be canceled.")

        third_assignments = PaperAssignment.objects.filter(
            selection_phase=self.selection_phase,
            paper_id=paper_id,
            stage=assignment_stage,
            is_third_reviewer=True
        )
        if not third_assignments.exists():
            raise ValueError("No third reviewer assignment found for this paper.")

        PaperReview.objects.filter(
            assignment__in=third_assignments,
            stage=review_stage
        ).delete()
        third_assignments.delete()

        conflict.third_reviewer = None
        if conflict.resolution_method == ResolutionMethodChoices.THIRD_REVIEWER:
            conflict.resolution_method = None
        conflict.final_decision = None
        conflict.resolved_by = None
        conflict.resolution_notes = ''
        conflict.resolved_at = None
        conflict.is_resolved = False
        conflict.save(update_fields=[
            'third_reviewer',
            'resolution_method',
            'final_decision',
            'resolved_by',
            'resolution_notes',
            'resolved_at',
            'is_resolved',
        ])

    def resolve_with_owner_vote(
        self,
        paper_id: str,
        owner,
        decision: str,
        notes: str,
        stage: str
    ):
        """
        Resolve a conflict with owner's final vote.

        Args:
            paper_id: Paper UUID
            owner: Owner user object
            decision: 'INCLUDED' or 'EXCLUDED'
            notes: Resolution notes
            stage: 'SCREENING' or 'FULL_TEXT'

        Returns:
            ConflictResolution object
        """
        from apps.selection.domain.models import ConflictResolution, PaperAssignment, PaperReview
        from apps.selection.domain.choices import AssignmentStageChoices, ResolutionMethodChoices
        from django.utils import timezone

        assignment_stage = AssignmentStageChoices.SCREENING if stage == 'SCREENING' else AssignmentStageChoices.FULLTEXT
        review_stage = 'SCREENING' if stage == 'SCREENING' else 'FULL_TEXT'

        # If a third reviewer was previously assigned, clear that path before owner decision.
        third_assignments = PaperAssignment.objects.filter(
            selection_phase=self.selection_phase,
            paper_id=paper_id,
            stage=assignment_stage,
            is_third_reviewer=True
        )
        if third_assignments.exists():
            PaperReview.objects.filter(
                assignment__in=third_assignments,
                stage=review_stage
            ).delete()
            third_assignments.delete()

        conflict, created = ConflictResolution.objects.update_or_create(
            selection_phase=self.selection_phase,
            paper_id=paper_id,
            stage=assignment_stage,
            defaults={
                'resolution_method': ResolutionMethodChoices.OWNER_VOTE,
                'third_reviewer': None,
                'final_decision': decision,
                'resolved_by': owner,
                'resolution_notes': notes,
                'is_resolved': True,
                'resolved_at': timezone.now()
            }
        )

        logger.info(f"[DISCREPANCY] Owner resolved conflict for paper {paper_id[:8]} with {decision}")

        return conflict

    def process_third_reviewer_decision(self, assignment, decision: str, notes: str, criterion_id: str = None, criterion_label: str = None):
        """
        Process third reviewer's decision and resolve the conflict.

        The third reviewer's decision is the tiebreaker.
        """
        from apps.selection.domain.models import PaperReview
        from apps.selection.domain.models import ConflictResolution
        from apps.selection.domain.choices import AssignmentStageChoices
        from django.utils import timezone

        review_stage = 'SCREENING' if assignment.stage == AssignmentStageChoices.SCREENING else 'FULL_TEXT'

        conflict = ConflictResolution.objects.filter(
            selection_phase=self.selection_phase,
            paper_id=assignment.paper_id,
            stage=assignment.stage
        ).first()
        if conflict and conflict.is_resolved and conflict.resolved_by_id != assignment.researcher_id:
            raise ValueError("This conflict was already resolved.")

        # Create or update the review
        review, _ = PaperReview.objects.update_or_create(
            assignment=assignment,
            stage=review_stage,
            defaults={
                'decision': decision,
                'notes': notes,
                'criterion_id': criterion_id,
                'criterion_label': criterion_label
            }
        )

        if conflict:
            conflict.final_decision = decision
            conflict.resolved_by = assignment.researcher
            conflict.is_resolved = True
            conflict.resolved_at = timezone.now()
            conflict.resolution_notes = f"Resolved by third reviewer: {notes}"
            conflict.save()

        logger.info(f"[DISCREPANCY] Third reviewer {assignment.researcher.username} resolved {assignment.paper_id[:8]} with {decision}")

        return review

    def get_eligible_third_reviewers(self, paper_id: str, stage: str) -> List:
        """
        Get team members eligible to be third reviewers.

        Excludes researchers who have already reviewed this paper and the
        project owner (owner should resolve via final vote).
        """
        from apps.selection.domain.models import PaperAssignment
        from apps.selection.domain.choices import AssignmentStageChoices

        assignment_stage = AssignmentStageChoices.SCREENING if stage == 'SCREENING' else AssignmentStageChoices.FULLTEXT

        # Get researchers who already have this paper
        existing_reviewers = PaperAssignment.objects.filter(
            selection_phase=self.selection_phase,
            paper_id=paper_id,
            stage=assignment_stage
        ).values_list('researcher_id', flat=True)

        # Get all team members excluding existing reviewers
        eligible = Membership.objects.filter(
            project_id=self.selection_phase.project_id,
            role__in=['OWNER', 'RESEARCHER']
        ).exclude(
            user_id__in=existing_reviewers
        ).exclude(
            user_id=self.selection_phase.project.owner_id
        ).select_related('user')

        return [m.user for m in eligible]
