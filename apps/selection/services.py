"""
Selection Distribution Service

Implements the greedy algorithm for balanced paper distribution 
among researchers based on workload capacity.
"""

from __future__ import annotations
import logging
from typing import Dict, List, Tuple, TYPE_CHECKING
from dataclasses import dataclass

from apps.project.structure.models.project_models import Membership
from apps.project.facade import get_project_facade

if TYPE_CHECKING:
    from apps.selection.models import ConflictResolution

logger = logging.getLogger(__name__)


@dataclass
class PaperInfo:
    """Paper information with word count"""
    paper_id: str
    title: str
    pages: int  # Using 'pages' field to store word count for consistency
    

@dataclass
class ResearcherCapacity:
    """Researcher workload capacity"""
    user_id: int
    username: str
    workload_hours: int
    remaining_capacity: float
    assigned_papers: List[str]
    
    def __lt__(self, other):
        """For sorting by remaining capacity (ascending)"""
        return self.remaining_capacity < other.remaining_capacity


class PaperDistributionService:
    """
    Service for distributing papers among researchers using a greedy algorithm.
    
    Algorithm:
    1. Calculate total pages across all papers × total_reviews_per_paper
    2. Calculate researcher capacity proportional to workload hours
    3. Assign papers greedily: largest paper → researcher with most capacity
    4. Ensure no researcher gets same paper twice
    """
    
    def __init__(self, project_id: int):
        self.project_id = project_id
        self.project_facade = get_project_facade()
        
    def distribute_papers(
        self,
        total_reviews_per_paper: int = 2
    ) -> Dict[str, List[str]]:
        """
        Distribute papers among researchers.
        
        Args:
            total_reviews_per_paper: Number of reviewers per paper
            
        Returns:
            Distribution dict: {user_id: [paper_ids]}
            
        Raises:
            ValueError: If insufficient workload capacity or no papers/researchers
        """
        logger.info(f"[DISTRIBUTION] Starting for project {self.project_id}")
        
        # 1. Get researchers with workload
        researchers = self._get_researchers_with_workload()
        if not researchers:
            raise ValueError("No researchers with workload assigned to project")
        
        # 2. Get papers with page counts
        papers = self._get_papers_with_pages()
        if not papers:
            raise ValueError("No papers available for distribution")
        
        # 3. Calculate capacities
        capacities = self._calculate_capacities(researchers, papers, total_reviews_per_paper)
        
        # 4. Distribute using greedy algorithm
        distribution = self._greedy_distribution(papers, capacities, total_reviews_per_paper)
        
        logger.info(f"[DISTRIBUTION] Completed: {len(papers)} papers to {len(researchers)} researchers")
        return distribution
    
    def _get_researchers_with_workload(self) -> List[Tuple[int, str, int]]:
        """
        Get all team members with assigned workload for this project.
        Includes both OWNER and RESEARCHER roles.
        
        Returns:
            List of tuples: (user_id, username, workload_hours)
        """
        memberships = Membership.objects.filter(
            project_id=self.project_id,
            role__in=['OWNER', 'RESEARCHER'],
            workload_hours__gt=0
        ).select_related('user')
        
        researchers = [
            (m.user.id, m.user.username, m.workload_hours)
            for m in memberships
        ]
        
        # Sort by workload descending
        researchers.sort(key=lambda x: x[2], reverse=True)
        
        logger.info(f"[DISTRIBUTION] Found {len(researchers)} team members with workload")
        return researchers
    
    def _get_papers_with_pages(self) -> List[PaperInfo]:
        """
        Get papers from project facade with word count from abstract.
        
        For screening phase: uses abstract word count as workload metric.
        Each word represents a unit of reading work.
        
        Returns:
            List of PaperInfo objects sorted by word count descending
        """
        # Get studies from project facade
        studies = self.project_facade.get_studies_by_project(
            project_id=self.project_id,
            include_metadata=True
        )
        
        papers = []
        for study in studies:
            # Count words in abstract
            abstract = study.get('abstract') or ''
            
            # Fallback: use title if no abstract
            if not abstract.strip():
                abstract = study.get('title') or ''
            
            # Count words (split by whitespace)
            word_count = len(abstract.split())
            
            # Minimum 1 word to avoid division issues
            word_count = max(1, word_count)
            
            papers.append(PaperInfo(
                paper_id=study['id'],
                title=study['title'],
                pages=word_count  # Using 'pages' field to store word count
            ))
        
        # Sort by word count descending
        papers.sort(key=lambda p: p.pages, reverse=True)
        
        logger.info(f"[DISTRIBUTION] Found {len(papers)} papers (using abstract word count)")
        return papers
    
    def _calculate_capacities(
        self,
        researchers: List[Tuple[int, str, int]],
        papers: List[PaperInfo],
        total_reviews: int
    ) -> List[ResearcherCapacity]:
        """
        Calculate word capacity for each researcher based on workload proportion.
        
        Args:
            researchers: List of (user_id, username, workload_hours)
            papers: List of PaperInfo (pages field contains word count)
            total_reviews: Reviews per paper (multiplier)
            
        Returns:
            List of ResearcherCapacity objects
        """
        # Calculate totals
        total_words = sum(p.pages for p in papers) * total_reviews
        total_workload = sum(r[2] for r in researchers)
        
        capacities = []
        for user_id, username, workload in researchers:
            # Proportional capacity
            proportion = workload / total_workload
            capacity = proportion * total_words
            
            capacities.append(ResearcherCapacity(
                user_id=user_id,
                username=username,
                workload_hours=workload,
                remaining_capacity=capacity,
                assigned_papers=[]
            ))
        
        logger.info(
            f"[DISTRIBUTION] Total words: {total_words}, "
            f"Total workload: {total_workload} hours"
        )
        return capacities
    
    def _greedy_distribution(
        self,
        papers: List[PaperInfo],
        capacities: List[ResearcherCapacity],
        total_reviews: int
    ) -> Dict[str, List[str]]:
        """
        Greedy algorithm: assign papers to researchers with most capacity.
        
        Args:
            papers: Sorted papers (largest first)
            capacities: Researcher capacities
            total_reviews: Reviews needed per paper
            
        Returns:
            Distribution dict: {username: [paper_ids]}
        """
        # Track assignments per paper
        paper_assignments = {p.paper_id: 0 for p in papers}
        
        # Assign each paper the required number of times
        for paper in papers:
            for _ in range(total_reviews):
                # Sort capacities by remaining capacity (descending)
                capacities.sort(reverse=True)
                
                # Find first researcher who doesn't have this paper
                assigned = False
                for researcher in capacities:
                    if paper.paper_id not in researcher.assigned_papers:
                        # Assign paper
                        researcher.assigned_papers.append(paper.paper_id)
                        researcher.remaining_capacity -= paper.pages
                        paper_assignments[paper.paper_id] += 1
                        assigned = True
                        
                        logger.debug(
                            f"[DISTRIBUTION] Assigned {paper.title[:30]} ({paper.pages} words) "
                            f"to {researcher.username} (capacity left: {researcher.remaining_capacity:.1f})"
                        )
                        break
                
                if not assigned:
                    logger.warning(
                        f"[DISTRIBUTION] Could not assign paper {paper.title} "
                        f"(all researchers already have it or insufficient capacity)"
                    )
        
        # Convert to output format
        distribution = {
            r.username: r.assigned_papers
            for r in capacities
        }
        
        # Log summary
        for username, papers_list in distribution.items():
            logger.info(f"[DISTRIBUTION] {username}: {len(papers_list)} papers assigned")
        
        return distribution


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
        from apps.selection.models import PaperReview, AssignmentStageChoices
        
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
        from apps.selection.models import PaperAssignment, PaperReview, SelectionDecisionChoices, AssignmentStageChoices
        
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
        from apps.selection.models import (
            PaperAssignment, PaperReview, ConflictResolution,
            SelectionDecisionChoices, AssignmentStageChoices
        )
        
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
        from apps.selection.models import (
            PaperAssignment, PaperReview, ConflictResolution,
            SelectionDecisionChoices, AssignmentStageChoices
        )
        
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
        from apps.selection.models import PaperAssignment, PaperReview, ConflictResolution, AssignmentStageChoices
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
        from apps.selection.models import (
            PaperAssignment, ConflictResolution, 
            AssignmentStageChoices, ResolutionMethodChoices
        )
        
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
    ) -> ConflictResolution:
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
        from apps.selection.models import ConflictResolution, AssignmentStageChoices, ResolutionMethodChoices
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
        from apps.selection.models import (
            PaperReview, ConflictResolution, AssignmentStageChoices
        )
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
        from apps.selection.models import PaperAssignment, AssignmentStageChoices
        
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
