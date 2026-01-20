from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages

from apps.project.decorators import project_member_required, build_design_url
from apps.design.exceptions.eligibility_criteria_exceptions import CreationError, NotFoundError, UpdateError
from apps.design.eligibility_criteria.models.eligibility_criteria import EligibilityCriterion
from apps.design.eligibility_criteria.services.eligibility_criterion_services import EligibilityCriterionService
from apps.design.eligibility_criteria.selectors import EligibilityCriterionSelector
from apps.design.design_phase_logic.services.design_phase_service import DesignPhaseService
from apps.design.design_phase_logic.selectors import DesignPhaseSelector
from apps.design.design_phase_logic.models.design_phase import DesignPhase

eligibility_service = EligibilityCriterionService()
design_phase_service = DesignPhaseService()


@project_member_required
def open_eligibility_criteria_panel(request, project_id, project):
    status_filter = request.GET.get('status')

    current_stage_plan = DesignPhaseSelector.get_current_stage_plan(project_id)
    timeline_stages = DesignPhaseSelector.get_design_timeline_context(project_id)

    inclusion_criteria = EligibilityCriterionSelector.get_inclusion_criteria(project_id, status_filter=status_filter)
    exclusion_criteria = EligibilityCriterionSelector.get_exclusion_criteria(project_id, status_filter=status_filter)

    context = {
        'project': project,
        'inclusion_criteria': inclusion_criteria,
        'exclusion_criteria': exclusion_criteria,
        'timeline_stages': timeline_stages,
        'current_stage_plan': current_stage_plan,
        'current_status_filter': status_filter,
        'active_tab': 'eligibility_criteria_panel',
        'is_owner': project.owner == request.user,
        'current_stage_value': project.design_phase.current_stage,
        'is_editable': project.design_phase.current_stage == DesignPhase.DesignStage.CRITERIA_DEFINITION,
    }
    return render(request, 'eligibility_criteria_panel.html', context)


@project_member_required
@require_POST
def create_eligibility_criterion(request, project_id, project):
    try:
        description = request.POST.get('description', '').strip()
        motivation = request.POST.get('motivation', '').strip()
        criteria_type = request.POST.get('type', '')

        if not description:
            return JsonResponse({'success': False, 'error': 'Description is required'})

        if criteria_type not in [EligibilityCriterion.CriterionType.INCLUSION,
                                 EligibilityCriterion.CriterionType.EXCLUSION]:
            return JsonResponse({'success': False, 'error': 'Invalid criterion type'})

        criterion = eligibility_service.create_eligibility_criterion(
            description=description,
            motivation=motivation,
            project_id=project.id,
            researcher=request.user,
            criteria_type=criteria_type
        )

        return JsonResponse({
            'success': True,
            'criterion_id': criterion.id,
            'description': criterion.description,
            'motivation': criterion.motivation,
            'status': criterion.status,
            'message': 'Criterion created successfully'
        })

    except (CreationError, NotFoundError) as e:
        return JsonResponse({'success': False, 'error': str(e)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Unexpected error: {str(e)}'}, status=500)


@project_member_required
@require_POST
def update_eligibility_criterion(request, project_id, criterion_id, project):
    try:
        description = request.POST.get('description', '').strip()
        motivation = request.POST.get('motivation', '').strip()

        if not description:
            return JsonResponse({'success': False, 'error': 'Description is required'})

        criterion = eligibility_service.update_eligibility_criterion(
            criterion_id=criterion_id,
            user=request.user,
            description=description,
            motivation=motivation
        )
        return JsonResponse({
            'success': True,
            'criterion_id': criterion.id,
            'description': criterion.description,
            'motivation': criterion.motivation,
            'status': criterion.status,
            'message': 'Criterion updated successfully'
        })

    except (UpdateError, NotFoundError) as e:
        return JsonResponse({'success': False, 'error': str(e)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@project_member_required
@require_POST
def approve_eligibility_criterion(request, project_id, criterion_id, project):
    try:
        justification = request.POST.get('justification', '')
        criterion = eligibility_service.approve_eligibility_criterion(
            criterion_id,
            request.user,
            justification=justification
        )
        
        # Notify criterion author
        try:
            from apps.notification.models import Notification
            if criterion.author_id != request.user.id:
                Notification.objects.create(
                    recipient_id=criterion.author_id,
                    sender=request.user,
                    type='CRITERION_APPROVED',
                    title='Eligibility Criterion Approved',
                    custom_message=f'{request.user.get_full_name() or request.user.username} has approved your eligibility criterion.',
                    project_id=project_id
                )
        except Exception:
            pass
        
        return JsonResponse({
            'success': True,
            'criterion_id': criterion.id,
            'status': criterion.status,
            'message': 'Criterion approved successfully'
        })
    except (UpdateError, NotFoundError) as e:
        return JsonResponse({'success': False, 'error': str(e)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@project_member_required
@require_POST
def reject_eligibility_criterion(request, project_id, criterion_id, project):
    try:
        justification = request.POST.get('justification', '')
        criterion = eligibility_service.reject_eligibility_criterion(
            criterion_id,
            request.user,
            justification=justification
        )
        
        # Notify criterion author
        try:
            from apps.notification.models import Notification
            if criterion.author_id != request.user.id:
                Notification.objects.create(
                    recipient_id=criterion.author_id,
                    sender=request.user,
                    type='CRITERION_REJECTED',
                    title='Eligibility Criterion Rejected',
                    custom_message=f'{request.user.get_full_name() or request.user.username} has rejected your eligibility criterion.',
                    project_id=project_id
                )
        except Exception:
            pass
        
        return JsonResponse({
            'success': True,
            'criterion_id': criterion.id,
            'status': criterion.status,
            'message': 'Criterion rejected successfully'
        })
    except UpdateError as e:
        return JsonResponse({'success': False, 'error': str(e)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Unexpected error occurred'})


@project_member_required
@require_POST
def delete_eligibility_criterion(request, project_id, criterion_id, project):
    try:
        eligibility_service.delete_eligibility_criterion(criterion_id, user=request.user)
        return JsonResponse({'success': True, 'message': 'Criterion deleted successfully'})
    except EligibilityCriterion.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Criterion not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'An unexpected error occurred during deletion'})


@project_member_required
@require_POST
def consolidate_eligibility_stage(request, project_id, project):
    try:
        design_phase_service.consolidate_eligibility_criteria_stage(
            project_id=project_id,
            user=request.user
        )
        msg = "Stage consolidated successfully! Proceeding to Search Strategy."
        messages.success(request, msg, extra_tags='design')
        return redirect(build_design_url(project_id, 'strategies/'))

    except Exception as e:
        messages.error(request, f"Error consolidating stage: {str(e)}", extra_tags='design')
        return redirect(build_design_url(project_id, 'eligibility-criteria/'))
