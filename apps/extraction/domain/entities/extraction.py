# apps/extraction/domain/entities/extraction.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from .quote import Quote
from ..value_objects.extraction_status import ExtractionStatus
from ..exceptions.extraction_exceptions import (
    ExtractionValidationError,
    InvalidExtractionState
)


@dataclass
class Extraction:
    """Aggregate Root"""
    id: Optional[int]
    study_id: int
    assigned_to_user_id: Optional[int]
    status: ExtractionStatus
    quotes: List[Quote] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    extraction_order: int = 1
    max_quotes: int = 100

    def start_working(self):
        if self.status != ExtractionStatus.PENDING:
            raise InvalidExtractionState(
                "Solo se pueden iniciar extracciones pendientes"
            )
        self.status = ExtractionStatus.IN_PROGRESS
        self.started_at = datetime.now()

    def add_quote(self, quote: Quote):
        if self.status == ExtractionStatus.PENDING:
            self.start_working()

        if self.status != ExtractionStatus.IN_PROGRESS:
            raise InvalidExtractionState(
                "Solo se pueden agregar quotes a extracciones en progreso"
            )

        if len(self.quotes) >= self.max_quotes:
            raise ExtractionValidationError(
                f"No se pueden agregar más de {self.max_quotes} quotes"
            )

        quote.extraction_id = self.id
        self.quotes.append(quote)

    def complete(self, missing_mandatory_tags: List[str]):
        if self.status != ExtractionStatus.IN_PROGRESS:
            raise InvalidExtractionState(
                "Solo se pueden completar extracciones en progreso"
            )

        if not self.quotes:
            raise ExtractionValidationError(
                "No se puede completar una extracción sin quotes"
            )

        if missing_mandatory_tags:
            raise ExtractionValidationError(
                f"Faltan tags obligatorios: {', '.join(missing_mandatory_tags)}"
            )

        self.status = ExtractionStatus.DONE
        self.completed_at = datetime.now()

    @property
    def is_active(self) -> bool:
        return self.status == ExtractionStatus.IN_PROGRESS