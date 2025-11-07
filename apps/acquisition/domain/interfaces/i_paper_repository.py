from abc import ABC, abstractmethod
from typing import Iterable, Optional
from apps.acquisition.domain.entities.paper import Paper


class IPaperRepository(ABC):
    """Contract for persistence of Paper metadata."""

    @abstractmethod
    def save(self, paper: Paper) -> Paper:
        raise NotImplementedError

    @abstractmethod
    def list(self, limit: Optional[int] = None) -> Iterable[Paper]:
        raise NotImplementedError
