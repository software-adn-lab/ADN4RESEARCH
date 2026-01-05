from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils.dateparse import parse_date
from apps.project.structure.models.project_models import Project
from apps.design.api.contracts import IDesignManagement
from apps.design.api.providers import DesignManagementProvider
from apps.design.api.dtos import DesignScheduleDTO


@login_required
@require_http_methods(["GET"])
def configure_schedule_view(request, project_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)

    # Use the provider to get stage info, avoiding direct import of DesignPhase
    provider: IDesignManagement = DesignManagementProvider()
    all_stages = provider.get_design_stages_info()

    # Filter out FINISHED stage
    stages_info = [s for s in all_stages if s['key'] != 'FINISHED']

    context = {
        'project': project,
        'stages': stages_info
    }
    return render(request, 'project/configure_schedule.html', context)


@login_required
@require_http_methods(["POST"])
def save_schedule_action(request, project_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)

    # 1. Project Dates are read-only, so we don't update them here.
    # We just validate that the stages are consistent.

    schedule_dtos = []

    provider: IDesignManagement = DesignManagementProvider()
    all_stages = provider.get_design_stages_info()
    # Filter out FINISHED for input processing
    stages_to_process = [s for s in all_stages if s['key'] != 'FINISHED']

    try:
        rq_creation_start = None
        search_strategy_end = None

        for stage in stages_to_process:
            stage_key = stage['key']
            start_str = request.POST.get(f'stage_{stage_key}_start')
            end_str = request.POST.get(f'stage_{stage_key}_end')

            if not start_str or not end_str:
                raise ValueError(f"Dates missing for stage {stage['label']}")

            start_date = parse_date(start_str)
            end_date = parse_date(end_str)

            # Capture specific dates for auto-calculation
            if stage_key == 'RQ_CREATION':
                rq_creation_start = start_date
            if stage_key == 'SEARCH_STRATEGY':
                search_strategy_end = end_date

            schedule_dtos.append(DesignScheduleDTO(
                stage=stage_key,
                start_date=start_date,
                end_date=end_date
            ))

        # 3. Call Design API
        provider.initialize_design_schedule(project.id, schedule_dtos)

        # 4. Activate Phase and Auto-Calculate Dates
        design_phase = project.design_phase
        design_phase.is_active = True

        # Auto-calculate phase dates
        if rq_creation_start:
            design_phase.start_date = rq_creation_start
        if search_strategy_end:
            design_phase.end_date = search_strategy_end

        design_phase.save()

        messages.success(request, "Schedule configured and Design Phase started!")
        return redirect('design:dashboard', project_id=project.id)

    except ValueError as e:
        messages.error(request, str(e))
        return redirect('project:configure_schedule', project_id=project.id)
    except Exception as e:
        messages.error(request, f"Error saving schedule: {str(e)}")
        return redirect('project:configure_schedule', project_id=project.id)
