
import logging
from apps.design.search_strategy.models.search_strategy import SearchStrategy, SearchStrategyVersion
from apps.design.search_strategy.services.search_strategy_service import SearchStrategyService
from apps.design.research_question.services.question_services import ResearchQuestionService
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib import messages
import json
from django.http import Http404
from django.urls import reverse
from django.shortcuts import redirect

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
        logging.debug(f"Generating search string for strategy ID: {strategy.id if strategy else 'None'}")

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
                    v_id = int(version_id_to_load)
                    version = search_strategy_service.get_version_by_id(v_id)
                    initial_visual_data = version.json_definition
                    
                    messages.info(request, f"Loaded version {version.version_number} from history.")
                    
                except (ValueError, SearchStrategyVersion.DoesNotExist):
                    initial_visual_data = strategy.json_definition
                    messages.warning(request, "Could not load requested version. Loaded current draft instead.")
            else:
                initial_visual_data = strategy.json_definition
                
        except Exception as e:
            raise Http404("Error loading strategy builder.")
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
            'redirect_url': reverse('design:search_results_view', args=[strategy_id]), 
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
            'id',
            'strategy_id',
            'version_number',
            'final_search_string',
            'total_found',
            'created_at'
        )
        data = []
        for v in versions:
            data.append({
                'id': v['id'],  
                'strategy_id': v['strategy_id'], 
                'version': v['version_number'],
                'string': v['final_search_string'],
                'total_found': v['total_found'],
                'date': v['created_at'].strftime("%Y-%m-%d %H:%M")
            })
            
        return JsonResponse({'versions': data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def search_results_view(request, strategy_id):
    try:
        strategy = search_strategy_service.get_strategy_by_id(strategy_id)
        project = strategy.research_question.design_phase.project
        results_dto = search_strategy_service.get_search_results_dto(strategy_id)
        year_filter = request.GET.get('year')
        studies = getattr(results_dto, 'studies', []) if results_dto else []
        if year_filter and studies:
            studies = [s for s in studies if str(s.get('year')) == year_filter]
        context = {
            'project': project,
            'strategy': strategy,
            'results': results_dto, 
            'studies': studies, 
            'years_range': range(2025, 2000, -1), 
            'current_year_filter': year_filter,
            'timeline_stages': design_phase_service.get_design_timeline_context(project.id)
        }
        return render(request, 'search_results.html', context)
    except strategy.DoesNotExist:
        raise Http404("Strategy not found")

@login_required
@require_POST
def approve_strategy(request, strategy_id):
    try:
        strategy = search_strategy_service.change_strategy_status(
            strategy_id, 
            SearchStrategy.Status.APPROVED, 
            request.user
        )
        messages.success(request, f"Strategy approved successfully!")
        return redirect('design:open_search_strategy_panel', project_id=strategy.research_question.design_phase.project.id)
    except Exception as e:
        messages.error(request, str(e))
        return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required
@require_POST
def reject_strategy(request, strategy_id):
    try:
        strategy = search_strategy_service.change_strategy_status(
            strategy_id, 
            SearchStrategy.Status.REJECTED, 
            request.user
        )
        messages.warning(request, "Strategy rejected.")
        return redirect('design:open_search_strategy_panel', project_id=strategy.research_question.design_phase.project.id)
    except Exception as e:
        messages.error(request, str(e))
        return redirect(request.META.get('HTTP_REFERER', '/'))
        
@login_required
@require_POST
def delete_strategy_version(request, version_id):
    try:
        search_strategy_service.delete_strategy_version(version_id)
        return JsonResponse({'status': 'success', 'message': 'Version deleted successfully'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)