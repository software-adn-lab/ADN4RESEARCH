from dataclasses import dataclass
from apps.acquisition.domain.entities.search_strategy import SearchStrategy


@dataclass
class SearchRequested:
    strategy: SearchStrategy
