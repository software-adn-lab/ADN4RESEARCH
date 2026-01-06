from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class EligibilityCriterionDTO:
    id: int
    description: str
    motivation: str
    justification: str
    type: str
    status: str
    design_phase_id: int
    researcher_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    reviewed_by_id: Optional[int]
    reviewed_at: Optional[datetime]

    @property
    def type_label(self):
        return self.type.title()

    @property
    def status_label(self):
        return self.status.replace('_', ' ').title()
