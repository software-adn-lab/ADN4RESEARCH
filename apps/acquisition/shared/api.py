"""
Public API for the shared kernel.

This module provides common utilities used across all acquisition components.
"""

from .domain.normalizers import normalize_title, normalize_doi
from .domain.constants import (
    SUPPORTED_SOURCES,
    TRANSLATION_STATUS_READY,
    TRANSLATION_STATUS_NOT_SUPPORTED,
    DISCOVERY_RESULT_COMPLETE,
    DISCOVERY_RESULT_PARTIAL,
)
from .domain.exceptions import DomainException, DomainValidationError

__all__ = [
    # Normalizers
    "normalize_title",
    "normalize_doi",
    # Constants
    "SUPPORTED_SOURCES",
    "TRANSLATION_STATUS_READY",
    "TRANSLATION_STATUS_NOT_SUPPORTED",
    "DISCOVERY_RESULT_COMPLETE",
    "DISCOVERY_RESULT_PARTIAL",
    # Exceptions
    "DomainException",
    "DomainValidationError",
]
