from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime


@dataclass
class FindingSection:
    """
    Represents a section of findings to be exported.
    """
    title: str
    content: str
    subsections: List['FindingSection'] = field(default_factory=list)


@dataclass
class ExportPackage:
    """
    Container for all data to be exported.
    """
    project_title: str
    generated_at: datetime
    
    # Metadata
    total_studies: int
    themes: List[str]
    
    # Propositions/Findings
    propositions: List[Dict[str, Any]]
    
    # Visualizations data
    bibliometric_data: Dict[str, Any]
    synthesis_matrix: Dict[str, Any]
    
    # Narrative sections
    sections: List[FindingSection] = field(default_factory=list)
