from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from apps.project.decorators import project_member_required


@login_required
@project_member_required
def dashboard_view(request, project_id, project):
    """
    Placeholder dashboard.
    Currently redirects to the stages router, but serves as the entry point
    after schedule configuration.
    """
    return redirect('design:design_stages', project_id=project_id)
