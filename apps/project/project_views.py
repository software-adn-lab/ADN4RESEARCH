from django.shortcuts import redirect
from apps.project.models import ProjectPhase
from django.contrib.auth.decorators import login_required

@login_required
def design_stages_view(request, project_id):
    """
    Router: Recibe el clic del Timeline y redirige a la vista específica de la etapa.
    """
    target_stage = request.GET.get('target_stage')
    
    # Mapa de navegación: Etapa -> URL Name
    stage_map = {
        ProjectPhase.Stage.RQ_CREATION: 'design:questions_history',
        ProjectPhase.Stage.RQ_DISCUSSION: 'design:question_discussion_panel',
        # ProjectPhase.Stage.CRITERIA_DEFINITION: 'design:criteria_workspace', (Futuro)
        # ProjectPhase.Stage.SEARCH_STRATEGY: 'design:search_strategy_workspace', (Futuro)
    }

    # Redirección por defecto a creación si no se encuentra la etapa
    url_name = stage_map.get(target_stage, 'design:questions_history')
    
    return redirect(url_name, project_id=project_id)