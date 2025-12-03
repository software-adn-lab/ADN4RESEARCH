"""
Shared testing mocks.

Este módulo contiene:
- Mock connectors para Feature 2 (Discovery) y Feature 3 (Consolidation)
- Mock factories para Feature 4 (Downloads)
"""

from .downloads import (
    build_fulltext_service_with_mocks,
    build_manual_upload_service_with_mocks,
)

__all__ = [
    "build_fulltext_service_with_mocks",
    "build_manual_upload_service_with_mocks",
]
