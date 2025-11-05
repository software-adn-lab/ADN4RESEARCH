from abc import ABC, abstractmethod
from typing import Iterable


class BaseConnector(ABC):
    """Base connector with a small contract for search."""

    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> Iterable[dict]:
        raise NotImplementedError
