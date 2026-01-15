"""
Concrete implementation of IProjectManagement interface.

This provider delegates to existing ProjectService while exposing a clean interface.
"""

from typing import List, Optional
from django.contrib.auth.models import User

from apps.project.api.contracts import IProjectManagement
from apps.project.api.dtos import ProjectDTO, ProjectMemberDTO
from apps.project.structure.services.project_services import ProjectService
from apps.project.structure.models.project_models import Project


class ProjectManagementProvider(IProjectManagement):
    """
    Concrete implementation of IProjectManagement.
    - Adapts existing ProjectService to new interface contract
    - Converts models to DTOs
    """

    def __init__(self):
        self._service = ProjectService()

    def get_project(self, project_id: int, user: Optional[User] = None) -> ProjectDTO:
        """
        Get project as DTO.

        Delegates to ProjectService.get_project_by_id() and converts to DTO.
        """
        project = self._service.get_project_by_id(project_id, user)

        return ProjectDTO(
            id=project.id,
            title=project.title,
            owner_id=project.owner.id,
            owner_username=project.owner.username,
            general_objective=project.general_objective,
            specific_objectives=project.specific_objectives.values_list('description', flat=True),
            created_at=project.created_at,
            end_date=project.end_date.date() if project.end_date else None
        )

    def is_project_owner(self, project_id: int, user: User) -> bool:
        """
        Check ownership.

        Direct query to avoid loading full project object.
        """
        try:
            project = Project.objects.only('owner').get(pk=project_id)
            return project.owner == user
        except Project.DoesNotExist:
            return False

    def is_project_member(self, project_id: int, user: User) -> bool:
        """
        Check membership (owner or researcher).

        Optimized query: checks owner first (cheap), then memberships.
        """
        try:
            project = Project.objects.only('owner').get(pk=project_id)

            # Owner is always member
            if project.owner == user:
                return True

            # Check explicit memberships
            return project.memberships.filter(user=user).exists()

        except Project.DoesNotExist:
            return False

    def get_project_members(self, project_id: int) -> List[ProjectMemberDTO]:
        """
        Get members as DTOs.

        Delegates to existing service and converts to DTO list.
        """
        project = Project.objects.get(pk=project_id)
        members_qs = self._service.get_project_members(project)

        return [
            ProjectMemberDTO(
                user_id=m.user.id,
                username=m.user.username,
                email=m.user.email,
                role=m.role
            )
            for m in members_qs
        ]

    def get_project_dates(self, project_id: int) -> dict:
        """
        Get timeline dates.

        Optimized query: only fetches date fields.
        """
        project = Project.objects.only('created_at', 'end_date').get(pk=project_id)
        return {
            'created_at': project.created_at,
            'end_date': project.end_date
        }
