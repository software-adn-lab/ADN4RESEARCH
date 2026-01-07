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
    project_form = ProjectForm(request.POST)
    specific_objective_formset = SpecificObjectiveFormSet(request.POST, prefix='specific_objectives')
    expected_result_formset = ExpectedResultFormSet(request.POST, prefix='expected_results')

    if (project_form.is_valid() and
        specific_objective_formset.is_valid() and
            expected_result_formset.is_valid()):

        try:
            project = _create_project_from_forms(request.user, project_form, specific_objective_formset, expected_result_formset)
            messages.success(request, "Project Created Successfully")
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
            members=project_data['members']
        )
        return project
    except ProjectCreationError as e:
        project_form.add_error(None, str(e))
        raise e
