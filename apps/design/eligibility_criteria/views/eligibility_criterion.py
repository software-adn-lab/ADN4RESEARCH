import json
from apps.design.exceptions.eligibility_criteria_exceptions import CreationError, UpdateError
from apps.design.eligibility_criteria.models.eligibility_criteria import EligibilityCriterion
from apps.design.eligibility_criteria.services.eligibility_criterion_services import EligibilityCriterionService
from apps.project.services.project_services import ProjectService
from django.http import JsonResponse
from django.shortcuts import render

eligibility_service = EligibilityCriterionService()
project_service = ProjectService()

def open_eligibility_criteria_panel(request, project_id):
    """Render the eligibility criteria panel for a project."""
    project = project_service.get_project_by_id(
        project_id, 
        user=request.user,
        related_fields=['design_phase', 'owner']
    )
    inclusion_criteria = eligibility_service.get_inclusion_criteria(project_id)
    exclusion_criteria = eligibility_service.get_exclusion_criteria(project_id)
    timeline_stages = project_service.get_design_timeline_context(project_id)
    
    context = {
        'project': project,
        'inclusion_criteria': inclusion_criteria,
        'exclusion_criteria': exclusion_criteria,
        'timeline_stages': timeline_stages,
        'active_tab': 'eligibility_criteria_panel',
    }
    return render(request, 'eligibity_criteria_panel.html', context)

def create_eligibility_criterion(request, project_id):
    """Create a new eligibility criterion via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        project = project_service.get_project_by_id(
            project_id, 
            user=request.user, 
            related_fields=['design_phase', 'owner'] 
        )
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
            project=project,
            suggester=request.user,
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
        
    except CreationError as e:
        return JsonResponse({'success': False, 'error': str(e)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Unexpected error occurred'})

def update_eligibility_criterion(request, criterion_id):
    """Update an existing criterion via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        description = request.POST.get('description', '').strip()
        motivation = request.POST.get('motivation', '').strip()
        
        if not description:
            return JsonResponse({'success': False, 'error': 'Description is required'})
        
        criterion = eligibility_service.update_eligibility_criterion(
            criterion_id=criterion_id,
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
        
    except UpdateError as e:
        return JsonResponse({'success': False, 'error': str(e)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Unexpected error occurred'})

def approve_eligibility_criterion(request, criterion_id):
    """Approve a criterion via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        criterion = eligibility_service.approve_eligibility_criterion(criterion_id)
        return JsonResponse({
            'success': True,
            'criterion_id': criterion.id,
            'status': criterion.status,
            'message': 'Criterion approved successfully'
        })
    except UpdateError as e:
        return JsonResponse({'success': False, 'error': str(e)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Unexpected error occurred'})

def reject_eligibility_criterion(request, criterion_id):
    """Reject a criterion via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        criterion = eligibility_service.reject_eligibility_criterion(criterion_id)
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

def delete_eligibility_criterion(request, criterion_id):
    """Delete a criterion via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        eligibility_service.delete_eligibility_criterion(criterion_id)
        return JsonResponse({'success': True, 'message': 'Criterion deleted successfully'})
    except EligibilityCriterion.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Criterion not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'An unexpected error occurred during deletion'})