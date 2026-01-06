from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.core.exceptions import ValidationError
# REFACTORED: Import decorator from shared module
from apps.shared.decorators import project_member_required
from apps.design.design_phase_logic.selectors import DesignPhaseSelector
from apps.design.design_phase_logic.models.design_phase import DesignStagePlan


@project_member_required
@require_http_methods(["GET", "POST"])
def manage_schedule_view(request, project_id, project_dto):
    """
    GET: Renderiza modal con cronograma editable
    POST: Actualiza fechas de stages

    CHANGED: project parameter is now project_dto (dict from IProjectManagement)
    """
    # REFACTORED: Check ownership via IProjectManagement (will add later)
    # For now, we need project model - temporary workaround
    from apps.project.structure.models.project_models import Project
    project = Project.objects.get(pk=project_id)

    # Validar que sea owner
    if project.owner != request.user:
        messages.error(request, "Only project owner can manage schedule.")
        return redirect('design:questions:workspace', project_id=project_id)
    if request.method == "POST":
        try:
            return _update_schedule(request, project_id, project)
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('design:questions:workspace', project_id=project_id)
    # GET: Obtener cronograma actual
    all_stages = DesignStagePlan.objects.filter(
        phase_id=project_id).order_by('planned_start_date')
    current_stage = DesignPhaseSelector.get_current_stage(
        project_id) if all_stages.exists() else None
    context = {
        'project': project,
        'all_stages': all_stages,
        'current_stage': current_stage,
        'project_start': project.created_at.date(),
        'project_end': project.end_date.date() if project.end_date else None,
    }
    return render(request, 'design/schedule_manager_modal.html', context)
def _update_schedule(request, project_id, project):
    """Helper to update stage dates from POST data"""
    from datetime import datetime
    updated_count = 0
    project_start = project.created_at.date()
    project_end = project.end_date.date() if project.end_date else None
    for key, value in request.POST.items():
        if not value or value == "":
            continue
        # Format: stage_<STAGE_CODE>_<start|end>
        if key.startswith('stage_'):
            parts = key.split('_')
            if len(parts) < 3:
                continue
            stage_code = parts[1]
            field_type = parts[2]  # 'start' or 'end'
            try:
                new_date = datetime.strptime(value, '%Y-%m-%d').date()
                # VALIDATION: Date must be within project bounds
                if new_date < project_start:
                    raise ValidationError(
                        f"{stage_code}: Start date cannot be before project start ({project_start})"
                    )
                if project_end and new_date > project_end:
                    raise ValidationError(
                        f"{stage_code}: End date cannot be after project end ({project_end})"
                    )
                # Update stage plan
                stage_plan = DesignStagePlan.objects.get(
                    phase_id=project_id, stage=stage_code)
                if field_type == 'start':
                    stage_plan.planned_start_date = new_date
                elif field_type == 'end':
                    stage_plan.planned_end_date = new_date
                # VALIDATION: Start must be before end
                if stage_plan.planned_start_date >= stage_plan.planned_end_date:
                    raise ValidationError(
                        f"{stage_code}: Start date must be before end date"
                    )
                stage_plan.save()
                updated_count += 1
            except DesignStagePlan.DoesNotExist:
                continue
            except ValueError:
                messages.warning(
                    request, f"Invalid date format for {stage_code}")
    messages.success(
        request, f"Schedule updated successfully! ({updated_count} changes)")
    return redirect('design:questions:workspace', project_id=project_id)
