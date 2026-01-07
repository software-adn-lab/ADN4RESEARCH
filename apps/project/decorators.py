from functools import wraps
from django.http import Http404
from django.contrib.auth.decorators import login_required
from apps.project.structure.services.project_services import ProjectService
from apps.project.exceptions.project_exceptions import ProjectNotFoundError

project_service = ProjectService()


def build_design_url(project_id: int, path: str) -> str:
    return f'/project/{project_id}/design/{path}'


def project_member_required(view_func):
    @wraps(view_func)
    def wrapper(request, project_id, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())

        try:
            project = project_service.get_project_by_id(
                project_id=project_id,
                user=request.user,
                related_fields=['owner', 'research_framework', 'design_phase']
            )
        except ProjectNotFoundError:
            raise Http404("Project not found or access denied.")

        kwargs['project'] = project
        return view_func(request, project_id, *args, **kwargs)

    return wrapper
