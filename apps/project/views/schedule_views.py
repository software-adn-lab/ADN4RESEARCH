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
    provider: IDesignManagement = DesignManagementProvider()
    all_stages = provider.get_design_stages_info()
    stages_info = [s for s in all_stages if s['key'] != 'FINISHED']
    context = {
        'project': project,
        'stages': stages_info,
        'project_start': project.created_at.date(),
        'project_end': project.end_date.date() if project.end_date else None,
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
        # NEW: Extract and validate Design Phase dates FIRST
        phase_start_str = request.POST.get('design_phase_start')
        phase_end_str = request.POST.get('design_phase_end')

        if not phase_start_str or not phase_end_str:
            raise ValueError("Design Phase start and end dates are required")

        phase_start = parse_date(phase_start_str)
        phase_end = parse_date(phase_end_str)

        # Validate phase dates are within project bounds
        project_start = project.created_at.date()
        project_end = project.end_date.date() if project.end_date else None

        if phase_start < project_start:
            raise ValueError(f"Design Phase cannot start before project start ({project_start})")

        if project_end and phase_end > project_end:
            raise ValueError(f"Design Phase cannot end after project end ({project_end})")

        if phase_start >= phase_end:
            raise ValueError("Design Phase start must be before end date")

        # Continue with stage processing
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

            # NEW: Validate stage dates are within PHASE bounds
            if start_date < phase_start:
                raise ValueError(f"{stage['label']}: Cannot start before Design Phase start ({phase_start})")

            if end_date > phase_end:
                raise ValueError(f"{stage['label']}: Cannot end after Design Phase end ({phase_end})")

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

        # 4. Activate Phase and Set User-Provided Dates
        design_phase = project.design_phase
        design_phase.is_active = True

        # Use user-provided phase dates (not auto-calculated)
        design_phase.start_date = phase_start
        design_phase.end_date = phase_end

        design_phase.save()

        messages.success(request, "Schedule configured and Design Phase started!", extra_tags='project')
        return redirect('design:dashboard', project_id=project.id)

    except ValueError as e:
        messages.error(request, str(e), extra_tags='project')
        return redirect('project:configure_schedule', project_id=project.id)
    except Exception as e:
        messages.error(request, f"Error saving schedule: {str(e)}", extra_tags='project')
        return redirect('project:configure_schedule', project_id=project.id)
