import logging
from typing import List

logger = logging.getLogger(__name__)


class SelectionFacade:
    """
    Facade for the selection module.

    Provides clean interface for other modules (especially Extraction)
    to access selection results.
    """

    def __init__(self):
        pass

    def get_approved_fulltext_papers(self, project_id: int) -> List[str]:
        """
        Get list of paper IDs that were approved in fulltext review.

        This is the main endpoint for Extraction module.

        Args:
            project_id: Project ID

        Returns:
            List of paper UUID strings
        """
        from apps.selection.models import (
            SelectionPhase, PaperAssignment, PaperReview, ConflictResolution,
            SelectionDecisionChoices, AssignmentStageChoices, SubPhaseStatusChoices
        )

        try:
            selection_phase = SelectionPhase.objects.get(project_id=project_id)
        except SelectionPhase.DoesNotExist:
            return []

        # Check if fulltext is completed
        if selection_phase.fulltext_status != SubPhaseStatusChoices.COMPLETED:
            logger.warning(f"[FACADE] Fulltext phase not completed for project {project_id}")
            # Still return approved papers if any

        approved_papers = set()

        # 1. Get papers from resolved conflicts with INCLUDED
        resolved_included = ConflictResolution.objects.filter(
            selection_phase=selection_phase,
            stage=AssignmentStageChoices.FULLTEXT,
            is_resolved=True,
            final_decision=SelectionDecisionChoices.INCLUDED
        ).values_list('paper_id', flat=True)

        approved_papers.update(resolved_included)

        # 2. Get papers where all fulltext reviews are INCLUDED (no conflict)
        all_fulltext_assignments = PaperAssignment.objects.filter(
            selection_phase=selection_phase,
            stage=AssignmentStageChoices.FULLTEXT,
            is_third_reviewer=False
        )

        paper_ids = all_fulltext_assignments.values_list('paper_id', flat=True).distinct()

        for paper_id in paper_ids:
            if paper_id in approved_papers:
                continue

            # Check if in unresolved conflict
            has_unresolved_conflict = ConflictResolution.objects.filter(
                selection_phase=selection_phase,
                stage=AssignmentStageChoices.FULLTEXT,
                paper_id=paper_id,
                is_resolved=False
            ).exists()

            if has_unresolved_conflict:
                continue

            # Get all reviews for this paper
            reviews = PaperReview.objects.filter(
                assignment__selection_phase=selection_phase,
                assignment__paper_id=paper_id,
                assignment__stage=AssignmentStageChoices.FULLTEXT,
                stage='FULL_TEXT'
            ).exclude(decision=SelectionDecisionChoices.PENDING)

            if not reviews.exists():
                continue

            decisions = set(reviews.values_list('decision', flat=True))
            if decisions == {SelectionDecisionChoices.INCLUDED}:
                approved_papers.add(paper_id)

        logger.info(f"[FACADE] Found {len(approved_papers)} approved fulltext papers for project {project_id}")

        return list(approved_papers)

    def is_selection_complete(self, project_id: int) -> bool:
        """
        Check if selection phase is fully complete.
        """
        from apps.selection.models import SelectionPhase, SubPhaseStatusChoices

        try:
            selection_phase = SelectionPhase.objects.get(project_id=project_id)
            return (
                selection_phase.fulltext_status == SubPhaseStatusChoices.COMPLETED and
                selection_phase.fulltext_discussions_resolved
            )
        except SelectionPhase.DoesNotExist:
            return False


def get_selection_facade() -> SelectionFacade:
    """Factory function to get SelectionFacade instance"""
    return SelectionFacade()
