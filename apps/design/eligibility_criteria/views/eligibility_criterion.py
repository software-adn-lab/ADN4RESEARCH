import json
from apps.design.exceptions.eligibility_criteria_exceptions import CreationError, UpdateError
from apps.design.eligibility_criteria.models.eligibility_criteria import EligibilityCriterion
from apps.design.eligibility_criteria.services.eligibility_criterion_services import EligibilityCriterionService
from apps.project.models import Project
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect

eligibility_service = EligibilityCriterionService()

def open_eligibility_criteria_panel(request, project_id):
    """Render the eligibility criteria panel for a project."""
    project = get_object_or_404(Project, id=project_id)
    
    inclusion_criteria = eligibility_service.get_criterion_by_project_and_type(
        project_id=project_id, 
        criteria_type=EligibilityCriterion.CriterionType.INCLUSION
    )
    exclusion_criteria = eligibility_service.get_criterion_by_project_and_type(
        project_id=project_id, 
        criteria_type=EligibilityCriterion.CriterionType.EXCLUSION
    )
    
    context = {
        'project': project,
        'inclusion_criteria': inclusion_criteria,
        'exclusion_criteria': exclusion_criteria,
        'active_tab': 'eligibility_criteria_panel',
    }
    return render(request, 'eligibity_criteria_panel.html', context)

def create_eligibility_criterion(request, project_id):
    """Create a new eligibility criterion via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        project = get_object_or_404(Project, id=project_id)
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