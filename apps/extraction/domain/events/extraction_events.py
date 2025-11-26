from dataclasses import dataclass
from datetime import datetime

@dataclass
class ExtractionCompletedEvent:
    """Evento de dominio: Ocurre cuando una extracción se finaliza con éxito."""
    extraction_id: int
    study_id: int
    completed_at: datetime
    user_id: int