"""
Project API - Models.

This module re-exports models from Project module for external consumption.
Allows other modules to import via clean API without direct coupling.

USAGE (from Design module):
    from apps.project.api.models import BasePhase
    
    class DesignPhase(BasePhase):
        ...
"""

from apps.project.structure.models.project_models import BasePhase

__all__ = [
    'BasePhase',
]
