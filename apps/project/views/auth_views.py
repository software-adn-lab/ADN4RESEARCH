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


class RegisterForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Username',
            'autofocus': True
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Email'
        })
    )
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Last Name'
        })
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Password'
        })
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Confirm Password'
        })
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Username already exists')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already exists')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match')

        return cleaned_data


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


@require_GET
def register_view(request):
    """Register page view"""
    if request.user.is_authenticated:
        return redirect('project:list_projects')
    
    form = RegisterForm()
    return render(request, 'project/register.html', {'form': form})


@require_POST
def register_action(request):
    """Handle registration submission"""
    form = RegisterForm(request.POST)
    
    if form.is_valid():
        username = form.cleaned_data['username']
        email = form.cleaned_data['email']
        first_name = form.cleaned_data['first_name']
        last_name = form.cleaned_data['last_name']
        password = form.cleaned_data['password1']
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password
        )
        
        # Log the user in
        login(request, user)
        messages.success(request, f'Welcome {user.first_name}! Your account has been created successfully.')
        return redirect('project:list_projects')
    
    return render(request, 'project/register.html', {'form': form})


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
