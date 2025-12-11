from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class InterpretationFindingsDTO:
    """
    DTO que representa los hallazgos finales de interpretación de un proyecto.
    Usado para comunicación entre módulos y exportación.
    """
    project_id: str
    themes: List[Dict[str, Any]]
    propositions: List[Dict[str, Any]]
    synthesis_matrix: Dict[str, Any]
    generated_at: datetime

@dataclass
class ThemeDTO:
    """DTO para representar un tema."""
    id: int
    name: str
    description: str
    research_question: str
    subthemes: List[Dict[str, Any]]

@dataclass
class PropositionDTO:
    """DTO para representar una proposición/hallazgo."""
    id: int
    text: str
    status: str
    theme_name: str
    subtheme_name: str
    supporting_narrative: str
