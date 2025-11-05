from typing import List
from apps.acquisition.domain.entities.paper import Paper


class MockPaperRepository:
    """In-memory repository for tests and early development."""

    def __init__(self) -> None:
        self._store: List[Paper] = []
        self._next_id = 1

    def save(self, paper: Paper) -> Paper:
        if paper.id is None:
            paper.id = self._next_id
            self._next_id += 1
        self._store.append(paper)
        return paper

    def list(self, limit: int = 10):
        return list(self._store)[:limit]
