"""
Selection Distribution Service

Implements the greedy algorithm for balanced paper distribution
among researchers based on workload capacity.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass

from apps.project.structure.models.project_models import Membership
from apps.project.facade import get_project_facade

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
    1. Calculate total pages across all papers x total_reviews_per_paper
    2. Calculate researcher capacity proportional to workload hours
    3. Assign papers greedily: largest paper -> researcher with most capacity
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
