
from apps.design.search_strategy.services.search_strategy_service import SearchStrategyService
from apps.design.research_question.services.question_services import ResearchQuestionService
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib import messages
import json

from apps.project.services.project_services import ProjectService

from apps.design.shared.services.design_phase_service import DesignPhaseService

search_strategy_service = SearchStrategyService()
research_question_service = ResearchQuestionService()
project_service = ProjectService()
design_phase_service = DesignPhaseService()


@login_required
def open_search_strategy_panel(request, project_id):
    project = project_service.get_project_by_id(
        project_id,
        user=request.user,
        related_fields=['owner', 'design_phase']
    )
    protocol_questions = project.protocol_questions  # Usando la property que arreglamos en Project
    stage_end_date = design_phase_service.get_current_stage_deadline(project_id)
    timeline_stages = design_phase_service.get_design_timeline_context(project_id)

    context = {
        'project': project,
        'protocol_questions': protocol_questions,
        'stage_end_date': stage_end_date,
        'timeline_stages': timeline_stages,
        'active_tab': 'search_string',
    }
    return render(request, 'search_strategy_panel.html', context)


@login_required
@require_POST
def generate_and_save_search_string_for_question(request, question_id):
    try:
        strategy = search_strategy_service.get_strategy_for_question(question_id)

        if not strategy:
            return JsonResponse({'error': 'Strategy not found'}, status=404)
        updated_strategy = search_strategy_service.generate_and_save_search_string(
            strategy_id=strategy.id,
            user_id=request.user.id
        )

        return JsonResponse({
            'status': 'success',
            'final_search_string': updated_strategy.final_search_string,
            'json_definition': updated_strategy.json_definition
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def search_strategy_builder_view(request, project_id):
    project = project_service.get_project_by_id(
        project_id,
        user=request.user,
        related_fields=['owner', 'design_phase']
    )
    timeline_stages = design_phase_service.get_design_timeline_context(project_id)
    stage_end_date = design_phase_service.get_current_stage_deadline(project_id)
    question_id = request.GET.get('question_id')
    version_id_to_load = request.GET.get('version_id')
    selected_question = None
    strategy = None
    pool_keywords = []
    initial_visual_data = {}
    questions_list = research_question_service.get_questions_for_workspace(project_id, request.user)

    if question_id:
        try:
            selected_question = research_question_service.get_research_question_by_id(question_id, request.user)
            strategy = search_strategy_service.get_or_create_strategy(selected_question.id)
            pool_keywords = project_service.get_project_keyterms(project_id)
            if version_id_to_load:
                try:
                    # Cargamos datos históricos específicos
                    version = search_strategy_service.get_version_by_id(version_id_to_load)
                    initial_visual_data = version.json_definition
                    # Opcional: Avisar al usuario que está viendo una versión antigua
                    messages.info(request, f"Loaded version {version.version_number} from history.")
                except version.DoesNotExist:
                    pass  # Si falla, cargamos lo actual
            else:
                # Carga normal (Estado actual de la estrategia)
                initial_visual_data = strategy.json_definition
        except Exception:
            pass

    context = {
        'project': project,
        'timeline_stages': timeline_stages,
        'stage_end_date': stage_end_date,
        'active_tab': 'search_string', 
        'questions_list': questions_list,
        'selected_question': selected_question,
        'strategy': strategy,
        'pool_keywords': pool_keywords,
        'visual_data_json': json.dumps(initial_visual_data),
    }
    return render(request, 'search_strategy_builder.html', context)

@login_required
@require_POST
def save_visual_strategy(request, strategy_id):
    import json
    try:
        data = json.loads(request.body)
        visual_data = data.get('visual_data')
        
        if not visual_data:
            return JsonResponse({'error': 'No data provided'}, status=400)
        updated_strategy = search_strategy_service.save_strategy_from_visual_builder(
            strategy_id=strategy_id,
            visual_data=visual_data,
            user_id=request.user.id
        )
        
        return JsonResponse({
            'status': 'success',
            'redirect_url': '', # Aquí la URL de resultados si la tuvieras
            'final_string': updated_strategy.final_search_string
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_strategy_versions(request, question_id):
    try:
        strategy = search_strategy_service.get_strategy_for_question(question_id)
        
        if not strategy:
            return JsonResponse({'versions': []})
        versions = strategy.versions.all().order_by('-version_number').values(
            'version_number',
            'final_search_string',
            'total_found',
            'created_at'
        )
        data = []
        for v in versions:
            data.append({
                'version': v['version_number'],
                'string': v['final_search_string'],
                'total_found': v['total_found'],
                'date': v['created_at'].strftime("%Y-%m-%d %H:%M")
            })
            
        return JsonResponse({'versions': data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)