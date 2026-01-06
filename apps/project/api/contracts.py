from abc import ABC, abstractmethod
from typing import Optional, List
from django.contrib.auth.models import User


class IProjectManagement(ABC):
    """
    Interface for Design module to interact with Project module.

    CONSUMERS: Design (views, services)
    PURPOSE: Access project data, permissions, members without direct coupling

    This interface implements the Dependency Inversion Principle:
    - High-level Design module depends on abstraction (this interface)
    - Low-level Project module implements abstraction (Provider)
    - Both modules are decoupled and testable independently
    """

    @abstractmethod
    def get_project(self, project_id: int, user: Optional[User] = None) -> dict:
        """
        Get project basic information as DTO.

        Args:
            project_id: Project ID
            user: Optional user for permission filtering

        Returns:
            ProjectDTO dict with: id, title, owner_id, owner_username, created_at, end_date

        Raises:
            ProjectNotFoundError: If project doesn't exist or user has no access
        """
        pass

    @abstractmethod
    def is_project_owner(self, project_id: int, user: User) -> bool:
        """
        Check if user is project owner.

        Args:
            project_id: Project ID
            user: User to check

        Returns:
            True if user owns the project, False otherwise
        """
        pass

    @abstractmethod
    def is_project_member(self, project_id: int, user: User) -> bool:
        """
        Check if user is project member (owner or researcher).

        Args:
            project_id: Project ID
            user: User to check

        Returns:
            True if user is member (owner or explicit membership)
        """
        pass

    @abstractmethod
    def get_project_members(self, project_id: int) -> List[dict]:
        """
        Get all project members.

        Args:
            project_id: Project ID

        Returns:
            List of ProjectMemberDTO dicts with: user_id, username, email, role
        """
        pass

    @abstractmethod
    def get_project_dates(self, project_id: int) -> dict:
        """
        Get project timeline dates.

        Args:
            project_id: Project ID

        Returns:
            Dict with 'created_at' (datetime) and 'end_date' (date or None)
        """
        pass
