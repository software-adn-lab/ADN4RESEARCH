from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class TagDTO:
    """DTO para tags usados en payloads JSON."""
    id: int
    name: str
    color: Optional[str]

    @classmethod
    def from_model(cls, tag) -> "TagDTO":
        return cls(id=tag.id, name=tag.name, color=tag.color)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
        }

