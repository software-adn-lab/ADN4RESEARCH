import logging
from typing import Dict, List, Tuple

from apps.project.structure.models.project_models import Membership
from apps.project.facade import get_project_facade

from apps.selection.features.distribution.services import PaperInfo, ResearcherCapacity

logger = logging.getLogger(__name__)


class FulltextDistributionService:
    """
    Service for distributing papers for fulltext review using page count.

    Similar to PaperDistributionService but uses PDF page count instead of
    abstract word count as the workload metric.
    """

    def __init__(self, project_id: int, selection_phase):
        self.project_id = project_id
        self.selection_phase = selection_phase
        self.project_facade = get_project_facade()

    def distribute_papers(
        self,
        total_reviews_per_paper: int = 2
    ) -> Dict[str, List[str]]:
        """
        Distribute papers included in screening for fulltext review.

        Args:
            total_reviews_per_paper: Number of reviewers per paper

        Returns:
            Distribution dict: {username: [paper_ids]}
        """
        from apps.selection.features.screening.models import PaperReview
        from apps.selection.models.choices import AssignmentStageChoices

        logger.info(f"[FULLTEXT_DISTRIBUTION] Starting for project {self.project_id}")

        # 1. Get researchers with workload
        researchers = self._get_researchers_with_workload()
        if not researchers:
            raise ValueError("No researchers with workload assigned to project")

        # 2. Get included papers from screening with page counts
        papers = self._get_included_papers_with_pages()
        if not papers:
            raise ValueError("No papers included in screening for fulltext review")

        # 3. Calculate capacities based on page count
        capacities = self._calculate_capacities(researchers, papers, total_reviews_per_paper)

        # 4. Distribute using greedy algorithm
        distribution = self._greedy_distribution(papers, capacities, total_reviews_per_paper)

        logger.info(f"[FULLTEXT_DISTRIBUTION] Completed: {len(papers)} papers to {len(researchers)} researchers")
        return distribution

    def _get_researchers_with_workload(self) -> List[Tuple[int, str, int]]:
        """Get team members with workload"""
        memberships = Membership.objects.filter(
            project_id=self.project_id,
            role__in=['OWNER', 'RESEARCHER'],
            workload_hours__gt=0
        ).select_related('user')

        researchers = [
            (m.user.id, m.user.username, m.workload_hours)
            for m in memberships
        ]
        researchers.sort(key=lambda x: x[2], reverse=True)

        logger.info(f"[FULLTEXT_DISTRIBUTION] Found {len(researchers)} team members with workload")
        return researchers

    def _get_included_papers_with_pages(self) -> List[PaperInfo]:
        """
        Get papers that were included in screening phase with PDF page counts.
        """
        from apps.selection.features.screening.models import PaperAssignment, PaperReview
        from apps.selection.models.choices import SelectionDecisionChoices, AssignmentStageChoices

        # Get all paper IDs that have at least one INCLUDED decision in screening
        # A paper is considered included if its final resolution (or majority) is INCLUDED
        included_paper_ids = self._get_screening_included_papers()

        if not included_paper_ids:
            return []

        # Get page counts from acquisition
        from apps.acquisition.facade import get_acquisition_facade
        acquisition_facade = get_acquisition_facade()

        # Get studies with metadata
        all_studies = self.project_facade.get_studies_by_project(
            project_id=self.project_id,
            include_metadata=True
        )
        studies_by_id = {str(s['id']): s for s in all_studies}

        # Try to get PDF status for page counts
        try:
            statuses = acquisition_facade.get_study_status(list(included_paper_ids))
            status_by_id = {str(s.get('id') or s.get('study_id') or s.get('uuid')): s for s in statuses}
        except Exception:
            status_by_id = {}

        papers = []
        for paper_id in included_paper_ids:
            study = studies_by_id.get(paper_id, {})
            status = status_by_id.get(paper_id, {})

            # Get page count from status or study metadata
            page_count = status.get('page_count') or study.get('page_count') or 10  # Default 10 pages
            page_count = max(1, page_count)

            papers.append(PaperInfo(
                paper_id=paper_id,
                title=study.get('title', 'Unknown'),
                pages=page_count
            ))

        # Sort by page count descending
        papers.sort(key=lambda p: p.pages, reverse=True)

        logger.info(f"[FULLTEXT_DISTRIBUTION] Found {len(papers)} included papers (using PDF page count)")
        return papers

    def _get_screening_included_papers(self) -> set:
        """
        Get paper IDs that should proceed to fulltext review.

        A paper is included if:
        - It has a resolved conflict with INCLUDED decision, OR
        - All reviewers agreed on INCLUDED
        """
        from apps.selection.features.screening.models import PaperAssignment, PaperReview
        from apps.selection.features.discussion.models import ConflictResolution
        from apps.selection.models.choices import SelectionDecisionChoices, AssignmentStageChoices

        included_papers = set()

        # 1. Get papers from resolved conflicts with INCLUDED
        resolved_included = ConflictResolution.objects.filter(
            selection_phase=self.selection_phase,
            stage=AssignmentStageChoices.SCREENING,
            is_resolved=True,
            final_decision=SelectionDecisionChoices.INCLUDED
        ).values_list('paper_id', flat=True)

        included_papers.update(resolved_included)

        # 2. Get papers where all reviews are INCLUDED (no conflict)
        all_screening_assignments = PaperAssignment.objects.filter(
            selection_phase=self.selection_phase,
            stage=AssignmentStageChoices.SCREENING,
            is_third_reviewer=False
        )

        paper_ids = all_screening_assignments.values_list('paper_id', flat=True).distinct()

        for paper_id in paper_ids:
            # Skip if already in resolved conflicts
            if paper_id in included_papers:
                continue

            # Check if in unresolved conflict
            has_unresolved_conflict = ConflictResolution.objects.filter(
                selection_phase=self.selection_phase,
                stage=AssignmentStageChoices.SCREENING,
                paper_id=paper_id,
                is_resolved=False
            ).exists()

            if has_unresolved_conflict:
                continue

            # Get all reviews for this paper
            reviews = PaperReview.objects.filter(
                assignment__selection_phase=self.selection_phase,
                assignment__paper_id=paper_id,
                assignment__stage=AssignmentStageChoices.SCREENING,
                stage='SCREENING'
            ).exclude(decision=SelectionDecisionChoices.PENDING)

            if not reviews.exists():
                continue

            # Check if all agree on INCLUDED
            decisions = set(reviews.values_list('decision', flat=True))
            if decisions == {SelectionDecisionChoices.INCLUDED}:
                included_papers.add(paper_id)

        return included_papers

    def _calculate_capacities(
        self,
        researchers: List[Tuple[int, str, int]],
        papers: List[PaperInfo],
        total_reviews: int
    ) -> List[ResearcherCapacity]:
        """Calculate page capacity for each researcher"""
        total_pages = sum(p.pages for p in papers) * total_reviews
        total_workload = sum(r[2] for r in researchers)

        capacities = []
        for user_id, username, workload in researchers:
            proportion = workload / total_workload
            capacity = proportion * total_pages

            capacities.append(ResearcherCapacity(
                user_id=user_id,
                username=username,
                workload_hours=workload,
                remaining_capacity=capacity,
                assigned_papers=[]
            ))

        logger.info(f"[FULLTEXT_DISTRIBUTION] Total pages: {total_pages}, Total workload: {total_workload} hours")
        return capacities

    def _greedy_distribution(
        self,
        papers: List[PaperInfo],
        capacities: List[ResearcherCapacity],
        total_reviews: int
    ) -> Dict[str, List[str]]:
        """Greedy algorithm for fulltext distribution"""
        paper_assignments = {p.paper_id: 0 for p in papers}

        for paper in papers:
            for _ in range(total_reviews):
                capacities.sort(reverse=True)

                assigned = False
                for researcher in capacities:
                    if paper.paper_id not in researcher.assigned_papers:
                        researcher.assigned_papers.append(paper.paper_id)
                        researcher.remaining_capacity -= paper.pages
                        paper_assignments[paper.paper_id] += 1
                        assigned = True
                        break

                if not assigned:
                    logger.warning(f"[FULLTEXT_DISTRIBUTION] Could not assign paper {paper.title}")

        distribution = {r.username: r.assigned_papers for r in capacities}

        for username, papers_list in distribution.items():
            logger.info(f"[FULLTEXT_DISTRIBUTION] {username}: {len(papers_list)} papers assigned")

        return distribution
