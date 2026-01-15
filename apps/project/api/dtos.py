"""
Data Transfer Objects for Project API.

These DTOs define the data contracts between Project and external modules.
Using TypedDict for simple dicts with type hints, dataclass for immutable objects.
"""

from typing import TypedDict, Optional
from dataclasses import dataclass
from datetime import datetime, date


class ProjectDTO(TypedDict):
    """
    Minimal project data for external modules.

    Used by Design module to get project information without coupling to Project model.
    """
    id: int
    title: str
    owner_id: int
    owner_username: str
    general_objective: str
    specific_objectives: Optional[list[str]]
    created_at: datetime
    end_date: Optional[date]


class ProjectMemberDTO(TypedDict):
    """
    Project member information.

    Exposes user and role data without coupling to Membership model.
    """
    user_id: int
    username: str
    email: str
    role: str  # OWNER, RESEARCHER


@dataclass(frozen=True)
class ProjectPermissionResult:
    """
    Result of permission check.

    Immutable result object for permission queries.
    Using dataclass for structured data with validation.
    """
    has_permission: bool
    reason: str = ""  # If false, why denied (e.g., "Not a member", "Not owner")
