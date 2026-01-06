from django.shortcuts import render, redirect
from apps.design.design_phase_logic.selectors import DesignPhaseSelector
# REFACTORED: Import decorator from shared module (no longer coupled to Project)
from apps.shared.decorators import project_member_required


@project_member_required
def dashboard_view(request, project_id, project_dto):
    """
    Placeholder dashboard.
    Currently redirects to the stages router, but serves as the entry point
    after schedule configuration.

    CHANGED: project parameter is now project_dto (dict from IProjectManagement)
    """
    return redirect('design:design_stages', project_id=project_id)
