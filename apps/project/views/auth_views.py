from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django import forms
from django.contrib import messages
from apps.project.structure.models.project_models import Project


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Username',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Password'
        })
    )


@require_GET
def login_view(request):
    """Login page view"""
    if request.user.is_authenticated:
        return redirect('project:list_projects')
    
    form = LoginForm()
    return render(request, 'project/login.html', {'form': form})


@require_POST
def login_action(request):
    """Handle login submission"""
    form = LoginForm(request.POST)
    
    if form.is_valid():
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome {user.first_name or user.username}!')
            return redirect('project:list_projects')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'project/login.html', {'form': form})


@require_POST
def logout_action(request):
    """Handle logout"""
    from django.contrib.auth import logout as auth_logout
    auth_logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('project:login')


@login_required
@require_GET
def list_projects(request):
    """List all projects for the logged-in user with active phase info"""
    projects = Project.objects.all()
    
    # Enrich projects with active phase info
    projects_with_phases = []
    for project in projects:
        project_data = {
            'project': project,
            'active_phase': get_project_active_phase(project),
        }
        projects_with_phases.append(project_data)
    
    return render(request, 'project/project_list.html', {'projects_with_phases': projects_with_phases})


def get_project_active_phase(project):
    """
    Determine the active phase for a project based on phase status.
    
    Returns: Dictionary with 'phase_name' and 'url' keys
    """
    try:
        from apps.design.design_phase_logic.models.design_phase import DesignPhase
        
        # Check Design Phase
        try:
            design_phase = DesignPhase.objects.get(project=project)
            if design_phase.is_active:
                return {
                    'phase_name': 'Design',
                    'phase_url': f'/project/{project.id}/design/',
                    'phase_key': 'design'
                }
        except DesignPhase.DoesNotExist:
            pass
    except ImportError:
        pass
    
    # Check Extraction Phase (most commonly used after design)
    try:
        from apps.extraction.planning.models import ExtractionPhase
        
        try:
            extraction_phase = ExtractionPhase.objects.filter(project=project).first()
            if extraction_phase and extraction_phase.status != 'CLOSED':
                return {
                    'phase_name': 'Extraction',
                    'phase_url': f'/extraction/{extraction_phase.id}/',
                    'phase_key': 'extraction'
                }
        except ExtractionPhase.DoesNotExist:
            pass
    except ImportError:
        pass
    
    # Check Selection Phase if it exists
    try:
        from apps.selection.models import SelectionPhase
        
        try:
            selection_phase = SelectionPhase.objects.get(project=project)
            if selection_phase.is_active:
                return {
                    'phase_name': 'Selection',
                    'phase_url': f'/project/{project.id}/selection/',
                    'phase_key': 'selection'
                }
        except SelectionPhase.DoesNotExist:
            pass
    except (ImportError, AttributeError):
        pass
    
    # Check Acquisition Phase if it exists
    try:
        from apps.acquisition.models import AcquisitionPhase
        
        try:
            acquisition_phase = AcquisitionPhase.objects.get(project=project)
            if acquisition_phase.is_active:
                return {
                    'phase_name': 'Acquisition',
                    'phase_url': f'/acquisition/{project.id}/',
                    'phase_key': 'acquisition'
                }
        except AcquisitionPhase.DoesNotExist:
            pass
    except (ImportError, AttributeError):
        pass
    
    # Check Interpretation Phase if it exists
    try:
        from apps.interpretation.models import InterpretationPhase
        
        try:
            interpretation_phase = InterpretationPhase.objects.get(project=project)
            if interpretation_phase.is_active:
                return {
                    'phase_name': 'Interpretation',
                    'phase_url': f'/interpretation/{project.id}/',
                    'phase_key': 'interpretation'
                }
        except InterpretationPhase.DoesNotExist:
            pass
    except (ImportError, AttributeError):
        pass
    
    # Fallback to Design if no active phase found
    return {
        'phase_name': 'Design',
        'phase_url': f'/project/{project.id}/design/',
        'phase_key': 'design'
    }
