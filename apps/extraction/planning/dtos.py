from dataclasses import dataclass
from decimal import Decimal
from django.db.models import QuerySet


@dataclass
class ProtocolCoverageReport:
    """
    Value Object que representa el estado de cobertura del protocolo.
    
    Business Rules:
    - Solo se consideran tags DEDUCTIVOS aprobados
    - Una RQ está cubierta si tiene al menos un tag deductivo aprobado
    - La cobertura es completa cuando todas las RQs están cubiertas
    """
    is_fully_covered: bool
    missing_rqs: QuerySet  # QuerySet de ResearchQuestion
    total_rqs: int
    covered_count: int

    @property
    def coverage_ratio(self) -> Decimal:
        """Ratio de cobertura (0.0 - 1.0)."""
        if self.total_rqs == 0:
            return Decimal('1.0')
        return Decimal(self.covered_count) / Decimal(self.total_rqs)
    
    @property
    def coverage_ratio_percent(self) -> int:
        """Porcentaje de cobertura (0 - 100)."""
        return int(self.coverage_ratio * 100)
    
    @property
    def coverage_ratio_display(self) -> str:
        """Representación visual del porcentaje."""
        return f"{self.coverage_ratio_percent}%"
    
    @property
    def coverage_fraction_display(self) -> str:
        """Representación visual de la fracción."""
        return f"{self.covered_count}/{self.total_rqs}"

    @property
    def missing_rq_texts(self):
        """Lista de textos de RQs faltantes."""
        return [rq.question_text for rq in self.missing_rqs]
    
    @property
    def missing_rq_count(self) -> int:
        """Número de RQs faltantes."""
        return self.missing_rqs.count()