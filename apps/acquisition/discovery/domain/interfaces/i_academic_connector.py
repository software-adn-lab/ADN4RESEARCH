from abc import ABC, abstractmethod
from typing import Iterable, Optional, Dict, Any


class IAcademicConnector(ABC):
    """Contract for connectors to academic sources (Scopus, IEEE, etc.)."""

    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> Iterable[dict]:
        """
        Search the external source and yield raw results as dicts.

        Used for discovery (Feature 1 & 2).
        """

    @abstractmethod
    def find_metadata(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Find metadata for a specific study by title.

        Used for enrichment (Feature 3).

        Args:
            title: The exact or normalized title of the study

        Returns:
            Dictionary with metadata fields (doi, abstract, authors, year, etc.)
            or None if not found
        """
