from dataclasses import dataclass
from typing import Optional, List


@dataclass
class Paper:
    """Simple domain entity representing a paper (scaffold)."""

    id: Optional[int]
    title: str
    authors: List[str]
    abstract: Optional[str] = None
    source: Optional[str] = None

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<Paper title={self.title!r} source={self.source!r}>"
