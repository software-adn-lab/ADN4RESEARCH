"""
DiscoveryResult entity for the discovery domain.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any

from apps.acquisition.shared.domain.entities.study import Study


@dataclass
class DiscoveryResult:
    """Represents the result of a discovery operation."""
    studies: List[Study] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the discovery result to a dictionary."""
        return {
            "studies": [study.to_dict() for study in self.studies],
            "summary": self.summary
        }
