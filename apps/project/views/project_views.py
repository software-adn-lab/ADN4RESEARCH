from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.db import transaction
from django.contrib import messages

from apps.project.exceptions.project_exceptions import ProjectCreationError
from apps.project.forms import ProjectForm, SpecificObjectiveFormSet, ExpectedResultFormSet
from apps.project.structure.services.project_services import ProjectService

@login_required
@require_GET
def open_project_creation_screen(request):
    """
    Responsibility: Prepare and render the empty form for project creation.
    """
    context = {
        'project_form': ProjectForm(),
        'specific_objective_formset': SpecificObjectiveFormSet(prefix='specific_objectives'),
        'expected_result_formset': ExpectedResultFormSet(prefix='expected_results'),
        'action': 'Create'
    }
    return render(request, 'project/create_project.html', context)

@login_required
@require_POST
def save_project_action(request):
    """
    Responsibility: Process the form submission, validate, and save the project.
    If validation fails, re-renders the form with errors.
    """
    project_form = ProjectForm(request.POST)
    specific_objective_formset = SpecificObjectiveFormSet(request.POST, prefix='specific_objectives')
    expected_result_formset = ExpectedResultFormSet(request.POST, prefix='expected_results')
    
    if (project_form.is_valid() and 
        specific_objective_formset.is_valid() and 
        expected_result_formset.is_valid()):
        
        try:
            _create_project_from_forms(request.user, project_form, specific_objective_formset, expected_result_formset)
            messages.success(request, "Project Created Successfully")
            return redirect('design:hello')
        except ProjectCreationError as e:
            project_form.add_error(None, str(e))

    # If invalid, re-render context with bound forms containing errors
    context = {
        'project_form': project_form,
        'specific_objective_formset': specific_objective_formset,
        'expected_result_formset': expected_result_formset,
        'action': 'Create'
    }
    return render(request, 'project/create_project.html', context)

def _create_project_from_forms(user, project_form, specific_stats_formset, expected_res_formset):
    """
    Helper to extract data and call the service. Keeps the view controller thin (DRY).
    """
    project_data = project_form.cleaned_data
    
    # Prepare framework data
    framework_keys_list = project_data['framework_keys'] 
    framework_fields = {key: "" for key in framework_keys_list}
    
    # Extract objectives descriptions
    objectives_data = [
        form.cleaned_data['description'] 
        for form in specific_stats_formset 
        if form.cleaned_data.get('description')
    ]
    
    # Extract results descriptions
    results_data = [
        form.cleaned_data['description'] 
        for form in expected_res_formset 
        if form.cleaned_data.get('description')
    ]

    service = ProjectService()
    try:
        service.create_project_with_framework(
            project_title=project_data['title'],
            project_end_date=project_data['end_date'],
            summary=project_data['summary'],
            motivation=project_data['motivation'],
            general_objective=project_data['general_objective'],
            owner=user,
            framework_name=project_data['framework_name'],
            framework_fields=framework_fields,
            specific_objectives_data=objectives_data,
            expected_results_data=results_data,
            members=project_data['members']
        )
    except ProjectCreationError as e:
        project_form.add_error(None, str(e))
        # Re-raise to be caught by the view if we wanted to handle it there, 
        # but here we want to modify the form, so we need to return the modified form up the stack?
        # Actually, _create_project_from_forms is a helper. Let's make it return a boolean or let exception bubble up.
        # Better: let the view catch it.
        raise e
