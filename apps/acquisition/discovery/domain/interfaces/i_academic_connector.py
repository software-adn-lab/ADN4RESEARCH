from abc import ABC, abstractmethod
from typing import Iterable


class IAcademicConnector(ABC):
    """Contract for connectors to academic sources (Scopus, IEEE, etc.)."""

    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> Iterable[dict]:
        """Search the external source and yield raw results as dicts."""
