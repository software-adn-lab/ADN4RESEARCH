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

    def get_conflicts(self, stage: str) -> List[dict]:
        """
        Get all unresolved conflicts for a given stage.

        Args:
            stage: 'SCREENING' or 'FULL_TEXT'

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

        # Get all paper IDs for this stage
        paper_ids = PaperAssignment.objects.filter(
            selection_phase=self.selection_phase,
            stage=assignment_stage,
            is_third_reviewer=False
        ).values_list('paper_id', flat=True).distinct()

        for paper_id in paper_ids:
            # Check if already resolved
            existing_resolution = ConflictResolution.objects.filter(
                selection_phase=self.selection_phase,
                paper_id=paper_id,
                stage=assignment_stage
            ).first()

            if existing_resolution and existing_resolution.is_resolved:
                continue

            # Get reviews for this paper (exclude pending)
            reviews = PaperReview.objects.filter(
                assignment__selection_phase=self.selection_phase,
                assignment__paper_id=paper_id,
                assignment__stage=assignment_stage,
                stage=review_stage
            ).exclude(decision=SelectionDecisionChoices.PENDING).select_related('assignment__researcher')

            if not reviews.exists():
                continue

            # Check for conflict (different decisions)
            decisions = set(reviews.values_list('decision', flat=True))

            if len(decisions) > 1:
                # There's a conflict
                conflict_data = {
                    'paper_id': paper_id,
                    'reviews': list(reviews),
                    'decisions': list(decisions),
                    'resolution': existing_resolution,
                    'reviewers': [r.assignment.researcher for r in reviews]
                }
                conflicts.append(conflict_data)

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
                'is_resolved': False
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
        from apps.selection.domain.models import ConflictResolution
        from apps.selection.domain.choices import AssignmentStageChoices, ResolutionMethodChoices
        from django.utils import timezone

        assignment_stage = AssignmentStageChoices.SCREENING if stage == 'SCREENING' else AssignmentStageChoices.FULLTEXT

        conflict, created = ConflictResolution.objects.update_or_create(
            selection_phase=self.selection_phase,
            paper_id=paper_id,
            stage=assignment_stage,
            defaults={
                'resolution_method': ResolutionMethodChoices.OWNER_VOTE,
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

        # Update conflict resolution
        conflict = ConflictResolution.objects.filter(
            selection_phase=self.selection_phase,
            paper_id=assignment.paper_id,
            stage=assignment.stage
        ).first()

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

        Excludes researchers who have already reviewed this paper.
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
        ).select_related('user')

        return [m.user for m in eligible]
