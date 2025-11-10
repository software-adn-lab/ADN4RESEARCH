"""
Study entity for the discovery domain.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Study:
    """
    Represents a study found during the discovery process.

    Attributes:
        title: The title of the study
        link: The URL link to the study
        source: The academic source (e.g., 'scopus', 'ieee')
        doi: Optional DOI identifier for the study
    """
    title: str
    link: str
    source: str
    doi: Optional[str] = None
