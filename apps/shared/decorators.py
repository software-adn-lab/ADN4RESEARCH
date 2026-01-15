"""
Shared decorators for all modules.

This module contains decorators that are used across multiple modules.
Most notably the project_member_required decorator which validates project access.

These decorators use interfaces (IProjectManagement) to avoid coupling with Project module.
"""

from functools import wraps
from django.http import Http404
from django.contrib.auth.views import redirect_to_login

from apps.project.api import IProjectManagement, ProjectManagementProvider

_project_mgmt: IProjectManagement = ProjectManagementProvider()

def project_member_required(view_func):
    """
    Decorator to check if user is project member before accessing view.
    USAGE:
        @project_member_required
        def my_view(request, project_id, project_dto):
            # Access project_dto (not model)
            print(project_dto['title'])

    Args:
        view_func: View function to decorate

    Returns:
        Wrapped view function with authentication and membership validation

    Injects into kwargs:
        project_dto: ProjectDTO dict with id, title, owner_id, owner_username, dates

    Raises:
        Http404: If project not found or user not authorized
        Redirects to login if user not authenticated
    """
    @wraps(view_func)
    def wrapper(request, project_id, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        is_member = _project_mgmt.is_project_member(project_id, request.user)
        if not is_member:
            raise Http404("Project not found or access denied.")

        try:
            project_dto = _project_mgmt.get_project(project_id, request.user)
        except Exception:
            raise Http404("Project not found or access denied.")
        kwargs['project_dto'] = project_dto
        return view_func(request, project_id, *args, **kwargs)
    return wrapper


def build_design_url(project_id: int, path: str) -> str:
    """
    Build URL for design module views.

    Helper function to construct design module URLs consistently.

    Args:
        project_id: Project ID
        path: Path within design module (e.g., 'research-questions/')

    Returns:
        Full URL path

    Example:
        build_design_url(1, 'research-questions/')  → '/project/1/design/research-questions/'
    """
    return f'/project/{project_id}/design/{path}'
