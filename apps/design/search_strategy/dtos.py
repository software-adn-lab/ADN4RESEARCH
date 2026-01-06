from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class SearchStrategyDTO:
    id: int
    research_question_id: int
    status: str
    final_search_string: str
    json_definition: Dict[str, Any]
    total_studies_found: int
    created_by_id: Optional[int]
    created_at: datetime
    last_modified_by_id: Optional[int]
    reviewed_by_id: Optional[int]

    # Helper properties for template convenience
    @property
    def status_label(self):
        return self.status.replace('_', ' ').title()

    @property
    def json_str(self):
        import json
        return json.dumps(self.to_dict())

    def to_dict(self):
        return {
            'id': self.id,
            'research_question_id': self.research_question_id,
            'status': self.status,
            'final_search_string': self.final_search_string,
            'json_definition': self.json_definition,
            'total_studies_found': self.total_studies_found,
        }


@dataclass
class SearchStrategyVersionDTO:
    id: int
    strategy_id: int
    version_number: int
    final_search_string: str
    json_definition: Dict[str, Any]
    total_found: int
    status: str
    justification: Optional[str]
    created_at: datetime
    created_by_id: Optional[int]
