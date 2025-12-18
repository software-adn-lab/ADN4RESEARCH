from dataclasses import dataclass
from django.db.models import QuerySet


@dataclass
class ProtocolCoverageReport:
    """Value Object que representa el estado de cobertura del protocolo."""
    is_fully_covered: bool
    missing_rqs: QuerySet  # QuerySet de ResearchQuestion
    total_rqs: int
    covered_count: int

    @property
    def coverage_ratio_display(self) -> str:
        return f"{self.covered_count}/{self.total_rqs}"

    @property
    def missing_rq_texts(self):
        return [rq.question_text for rq in self.missing_rqs]