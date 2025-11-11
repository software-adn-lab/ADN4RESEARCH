"""
Public API for the discovery component.

This module provides the façade for external components to interact
with the discovery functionality.
"""

from .application.discovery_service import DiscoveryService
from .domain.entities.study import Study
from .domain.entities.discovery_result import DiscoveryResult
from .domain.interfaces.i_academic_connector import IAcademicConnector

__all__ = [
    "DiscoveryService",
    "Study",
    "DiscoveryResult",
    "IAcademicConnector",
]
