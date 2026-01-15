from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.db import transaction
from django.contrib import messages
from django.http import HttpResponseForbidden

from apps.project.exceptions.project_exceptions import ProjectCreationError
from apps.project.forms import ProjectForm, SpecificObjectiveFormSet, ExpectedResultFormSet
from apps.project.structure.services.project_services import ProjectService
from apps.project.structure.models.project_models import Project


@login_required
@require_GET
def open_project_creation_screen(request):
    from django.contrib.auth.models import User
    context = {
        'project_form': ProjectForm(),
        'specific_objective_formset': SpecificObjectiveFormSet(prefix='specific_objectives'),
        'expected_result_formset': ExpectedResultFormSet(prefix='expected_results'),
        'all_users': User.objects.all().order_by('username'),
        'action': 'Create'
    }
    return render(request, 'project/create_project.html', context)


@login_required
@require_POST
def save_project_action(request):
    project_form = ProjectForm(request.POST)
    specific_objective_formset = SpecificObjectiveFormSet(request.POST, prefix='specific_objectives')
    expected_result_formset = ExpectedResultFormSet(request.POST, prefix='expected_results')

    if (project_form.is_valid() and
        specific_objective_formset.is_valid() and
            expected_result_formset.is_valid()):

        try:
            project = _create_project_from_forms(request.user, project_form, specific_objective_formset, expected_result_formset)
            messages.success(request, "Project Created Successfully", extra_tags='project')
            return redirect('project:configure_schedule', project_id=project.id)
        except ProjectCreationError as e:
            project_form.add_error(None, str(e))
    context = {
        'project_form': project_form,
        'specific_objective_formset': specific_objective_formset,
        'expected_result_formset': expected_result_formset,
        'action': 'Create'
    }
    return render(request, 'project/create_project.html', context)


def _create_project_from_forms(user, project_form, specific_stats_formset, expected_res_formset):
    project_data = project_form.cleaned_data
    framework_keys_list = project_data['framework_keys']
    framework_fields = {key: "" for key in framework_keys_list}
    objectives_data = [
        form.cleaned_data['description']
        for form in specific_stats_formset
        if form.cleaned_data.get('description')
    ]
    results_data = [
        form.cleaned_data['description']
        for form in expected_res_formset
        if form.cleaned_data.get('description')
    ]
    
    # Parse members with workload
    members_workload = project_data.get('members_workload', [])
    
    service = ProjectService()
    try:
        project = service.create_project_with_framework(
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
            members_workload=members_workload  # Changed from 'members' to 'members_workload'
        )
        return project
    except ProjectCreationError as e:
        project_form.add_error(None, str(e))
        raise e


@login_required
@require_POST
def delete_project_action(request, project_id):
    """Delete a project (only owner can delete)"""
    project = get_object_or_404(Project, id=project_id)
    
    # Check if user is the owner
    if project.owner != request.user:
        return HttpResponseForbidden("You do not have permission to delete this project.")
    
    project_title = project.title
    
    try:
        with transaction.atomic():
            project.delete()
        messages.success(request, f'Project "{project_title}" has been deleted successfully.', extra_tags='project')
    except Exception as e:
        messages.error(request, f'Error deleting project: {str(e)}', extra_tags='project')
    
    return redirect('project:list_projects')
