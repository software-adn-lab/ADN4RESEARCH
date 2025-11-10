"""
Deduplicator service for removing duplicate studies.
"""
from typing import List

from apps.acquisition.domain.entities.study import Study


class Deduplicator:
    """
    Service for deduplicating studies based on title and DOI.
    """

    def deduplicate(self, studies: List[Study]) -> List[Study]:
        """
        Remove duplicate studies from the list.

        Args:
            studies: List of studies to deduplicate

        Returns:
            List of unique studies (stub implementation - returns input as-is)
        """
        return studies
