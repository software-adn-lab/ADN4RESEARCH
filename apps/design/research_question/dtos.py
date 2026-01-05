from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class ResearchQuestionDTO:
    id: int
    question: str
    motivation: str
    status: str
    status_label: str
    framework_fields: Dict[str, Any]
    researcher_name: str
    is_editable: bool
    created_at: datetime
    modified_at: datetime

    # Optional fields for detailed views
    justification: Optional[str] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    def to_dict(self):
        return {
            'id': self.id,
            'question': self.question,
            'motivation': self.motivation,
            'status': self.status,
            'status_label': self.status_label,
            'framework_fields': self.framework_fields,
            'researcher_name': self.researcher_name,
            'is_editable': self.is_editable,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'modified_at': self.modified_at.isoformat() if self.modified_at else None,
            'justification': self.justification,
        }

    @property
    def json_str(self):
        import json
        return json.dumps(self.to_dict())
