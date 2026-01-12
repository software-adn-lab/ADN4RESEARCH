"""
Context processors for theme app.
Makes data available to all templates.
"""
from apps.project.structure.models.project_models import Project, Membership


def sidebar_context(request):
    """
    Provide sidebar data to all templates.
    Includes user projects and their phases.
    """
    if not request.user.is_authenticated:
        return {
            'sidebar_projects': [],
            'user_name': '',
            'user_email': '',
        }
    
    # Get projects where user is member
    memberships = Membership.objects.filter(user=request.user).select_related('project')
    
    projects_data = []
    for membership in memberships:
        project = membership.project
        
        # Determine available phases for this project
        phases = []
        
        # Check Design phase
        try:
            from apps.design.design_phase_logic.models.design_phase import DesignPhase
            design_phase = DesignPhase.objects.filter(project=project).first()
            if design_phase:
                phases.append({
                    'name': 'Design',
                    'url': f'/project/{project.id}/design/',
                    'icon': 'design',
                    'active': design_phase.is_active,
                })
        except:
            pass
        
        # Check Selection phase
        try:
            from apps.selection.models import SelectionPhase
            selection_phase = SelectionPhase.objects.filter(project=project).first()
            if selection_phase:
                phases.append({
                    'name': 'Selection',
                    'url': f'/project/{project.id}/selection/',
                    'icon': 'selection',
                    'active': selection_phase.is_active,
                })
        except:
            pass
        
        # Check Acquisition phase
        try:
            from apps.acquisition.models import AcquisitionPhase
            acquisition_phase = AcquisitionPhase.objects.filter(project=project).first()
            if acquisition_phase:
                phases.append({
                    'name': 'Acquisition',
                    'url': f'/acquisition/{project.id}/',
                    'icon': 'acquisition',
                    'active': getattr(acquisition_phase, 'is_active', False),
                })
        except:
            pass
        
        # Check Extraction phase
        try:
            from apps.extraction.planning.models import ExtractionPhase
            extraction_phase = ExtractionPhase.objects.filter(project=project).first()
            if extraction_phase:
                phases.append({
                    'name': 'Extraction',
                    'url': f'/extraction/{extraction_phase.id}/',
                    'icon': 'extraction',
                    'active': extraction_phase.status != 'CLOSED',
                })
        except:
            pass
        
        # Check Interpretation phase
        try:
            from apps.interpretation.models import InterpretationPhase
            interpretation_phase = InterpretationPhase.objects.filter(project=project).first()
            if interpretation_phase:
                phases.append({
                    'name': 'Interpretation',
                    'url': f'/interpretation/{project.id}/',
                    'icon': 'interpretation',
                    'active': getattr(interpretation_phase, 'is_active', False),
                })
        except:
            pass
        
        projects_data.append({
            'id': project.id,
            'title': project.title,
            'phases': phases,
            'is_owner': membership.role == 'OWNER',
        })
    
    return {
        'sidebar_projects': projects_data,
        'user_name': request.user.get_full_name() or request.user.username,
        'user_email': request.user.email or f'{request.user.username}@example.com',
        'user_initials': ''.join([word[0].upper() for word in (request.user.get_full_name() or request.user.username).split()[:2]]),
    }
