from abc import ABC, abstractmethod
from typing import Iterable, Optional, Dict, Any


class IAcademicConnector(ABC):
    """Contract for connectors to academic sources."""

    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> Iterable[dict]:
        """Search the external source and yield raw results as dicts."""

    @abstractmethod
    def find_metadata(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Find metadata for a specific study by title.

        Args:
            title: The exact or normalized title of the study

        Returns:
            Dictionary with metadata fields or None if not found
        """
