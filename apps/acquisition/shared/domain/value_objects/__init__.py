"""
Value Objects para el dominio compartido de Acquisition.
"""

from .doi import DOI
from .study_status import StudyStatus
from .source import Source

__all__ = [
    "DOI",
    "StudyStatus",
    "Source",
]
