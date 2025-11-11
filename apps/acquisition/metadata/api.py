"""
Public API for the metadata component.

This module provides the façade for external components to interact
with the metadata operations (deduplication, normalization).
"""

from .domain.services.deduplicator import Deduplicator
from .domain.services.normalizers import normalize_title, normalize_doi

__all__ = [
    "Deduplicator",
    "normalize_title",
    "normalize_doi",
]
