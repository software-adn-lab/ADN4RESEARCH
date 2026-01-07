
from typing import TypedDict
from dataclasses import dataclass
from datetime import date

class QuestionDTO(TypedDict):
    """Datos mínimos de una pregunta de investigación."""
    id: int
    question: str


class CriterionDTO(TypedDict):
    """Datos mínimos de un criterio de elegibilidad."""
    id: int
    description: str
    
@dataclass(frozen=True) 
class DesignScheduleDTO:
    stage: str
    start_date: date
    end_date: date
