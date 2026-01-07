"""
Project API - Public Interface.

This module exposes the public API for Project module.
External modules (Design, Selection, Extraction) should ONLY import from here.

USAGE EXAMPLE (from Design module):
    from apps.project.api import IProjectManagement, ProjectManagementProvider
    from apps.project.api import BasePhase  # For model inheritance
    
    project_mgmt: IProjectManagement = ProjectManagementProvider()
    project_dto = project_mgmt.get_project(project_id, user)
    is_owner = project_mgmt.is_project_owner(project_id, user)
"""

from .contracts import IProjectManagement
from .providers import ProjectManagementProvider
from .dtos import ProjectDTO, ProjectMemberDTO, ProjectPermissionResult
from .models import BasePhase

__all__ = [
    # Interfaces (contracts)
    'IProjectManagement',

    # Providers (implementations)
    'ProjectManagementProvider',

    # DTOs (data transfer objects)
    'ProjectDTO',
    'ProjectMemberDTO',
    'ProjectPermissionResult',

    # Models (for inheritance)
    'BasePhase',
]
