from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SearchStrategy:
    """Represents an abstract search/query strategy."""

    query: str
    sources: List[str]
    max_results: Optional[int] = None
