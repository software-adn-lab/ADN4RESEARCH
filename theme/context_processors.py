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
            'current_project_id': None,
        }
    
    # Detect current project from URL
    current_project_id = None
    path = request.path
    import re
    # Match patterns like /project/1/design/ or /extraction/1/ or /acquisition/1/
    project_match = re.search(r'/(?:project|extraction|acquisition|interpretation|selection)/(\d+)/', path)
    if project_match:
        current_project_id = int(project_match.group(1))
    
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
                    'url': f'/project/{project.id}/design/dashboard',
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
        
        # Check Extraction phase
        try:
            from apps.extraction.planning.models import ExtractionPhase
            extraction_phase = ExtractionPhase.objects.filter(project=project).first()
            if extraction_phase:
                phases.append({
                    'name': 'Extraction',
                    'url': f'/project/{project.id}/extraction/',
                    'icon': 'extraction',
                    'active': extraction_phase.status != 'CLOSED',
                })
        except:
            pass
        
        # Check Interpretation phase
        try:
            from apps.interpretation.conclusion_assistant.models import InterpretationPhase
            interpretation_phase = InterpretationPhase.objects.filter(project=project).first()
            if interpretation_phase:
                phases.append({
                    'name': 'Interpretation',
                    'url': f'/interpretation/{project.id}/',
                    'icon': 'interpretation',
                    'active': getattr(interpretation_phase, 'is_active', False),
                })
        except ImportError:
            pass
        
        projects_data.append({
            'id': project.id,
            'title': project.title,
            'phases': phases,
            'is_owner': membership.role == 'OWNER',
        })
    
    # Get unread notifications count
    unread_notifications_count = 0
    try:
        from apps.notification.models import Notification
        unread_notifications_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
    except:
        pass
    
    return {
        'sidebar_projects': projects_data,
        'user_name': request.user.get_full_name() or request.user.username,
        'user_username': request.user.username,
        'user_initials': ''.join([word[0].upper() for word in (request.user.get_full_name() or request.user.username).split()[:2]]),
        'current_project_id': current_project_id,
        'unread_notifications_count': unread_notifications_count,
    }
