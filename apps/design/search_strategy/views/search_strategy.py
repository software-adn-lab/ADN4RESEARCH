import json
import logging

from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse

from apps.project.decorators import project_member_required, build_design_url
from apps.design.search_strategy.models.search_strategy import SearchStrategy, SearchStrategyVersion
from apps.design.search_strategy.services.search_strategy_service import SearchStrategyService
from apps.design.search_strategy.selectors import SearchStrategySelector
from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.design.research_question.selectors import ResearchQuestionSelector
from apps.design.design_phase_logic.services.design_phase_service import DesignPhaseService
from apps.design.design_phase_logic.selectors import DesignPhaseSelector
from apps.project.structure.services.project_services import ProjectService

search_strategy_service = SearchStrategyService()
research_question_service = ResearchQuestionService()
project_service = ProjectService()
design_phase_service = DesignPhaseService()


@project_member_required
def open_search_strategy_panel(request, project_id, project):
    protocol_questions = project.protocol_questions
    current_stage_plan = DesignPhaseSelector.get_current_stage_plan(project_id)
    timeline_stages = DesignPhaseSelector.get_design_timeline_context(project_id)

    context = {
        'project': project,
        'protocol_questions': protocol_questions,
        'current_stage_plan': current_stage_plan,
        'timeline_stages': timeline_stages,
        'active_tab': 'search_string',
    }
    return render(request, 'search_strategy_panel.html', context)


@project_member_required
@require_POST
def generate_and_save_search_string_for_question(request, project_id, question_id, project):
    try:
        # Use Selector to get DTO
        strategy_dto = SearchStrategySelector.get_by_question_id(question_id)
        logging.debug(f"Generating search string for strategy ID: {strategy_dto.id if strategy_dto else 'None'}")

        if not strategy_dto:
            return JsonResponse({'error': 'Strategy not found'}, status=404)

        updated_strategy = search_strategy_service.generate_and_save_search_string(
            strategy_id=strategy_dto.id,
            user_id=request.user.id
        )

        return JsonResponse({
            'status': 'success',
            'final_search_string': updated_strategy.final_search_string,
            'json_definition': updated_strategy.json_definition
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@project_member_required
def search_strategy_builder_view(request, project_id, project):
    timeline_stages = DesignPhaseSelector.get_design_timeline_context(project_id)
    stage_end_date = DesignPhaseSelector.get_current_stage_plan(project_id)
    question_id = request.GET.get('question_id')
    version_id_to_load = request.GET.get('version_id')
    selected_question = None
    strategy = None
    pool_keywords = []
    initial_visual_data = {}
    questions_list = ResearchQuestionSelector.get_list_for_workspace(project_id, request.user)

    if question_id:
        try:
            selected_question = ResearchQuestionSelector.get_by_id(question_id, request.user)
            # This is a write/create operation, so we keep using the Service
            strategy = search_strategy_service.get_or_create_strategy(selected_question.id)
            pool_keywords = project_service.get_project_keyterms(project_id)

            if version_id_to_load:
                try:
                    v_id = int(version_id_to_load)
                    version = SearchStrategySelector.get_version_by_id(v_id)
                    if version:
                        initial_visual_data = version.json_definition
                        messages.info(request, f"Loaded version {version.version_number} from history.", extra_tags='design')
                    else:
                        # Fallback if version not found
                        initial_visual_data = strategy.json_definition
                        messages.warning(request, "Could not load requested version. Loaded current draft instead.", extra_tags='design')
                except ValueError:
                    initial_visual_data = strategy.json_definition
                    messages.warning(request, "Invalid version ID. Loaded current draft instead.", extra_tags='design')
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


@project_member_required
@require_POST
def save_visual_strategy(request, project_id, strategy_id, project):
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
            'redirect_url': build_design_url(project_id, f'strategies/{strategy_id}/results/'),
            'final_string': updated_strategy.final_search_string
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@project_member_required
@require_POST
def preview_search_string(request, project_id, project):
    try:
        data = json.loads(request.body)
        visual_data = data.get('visual_data')

        if not visual_data:
            return JsonResponse({'error': 'No data provided'}, status=400)

        # Use the service's builder directly to generate the string
        # We don't save anything, just return the string
        preview_string = search_strategy_service.string_builder.build_from_json(visual_data)

        return JsonResponse({
            'status': 'success',
            'preview_string': preview_string
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@project_member_required
def get_strategy_versions(request, project_id, question_id, project):
    try:
        # Use Selector to get DTO
        strategy_dto = SearchStrategySelector.get_by_question_id(question_id)

        if not strategy_dto:
            return JsonResponse({'versions': []})

        # Use Selector to get versions list
        versions_data = SearchStrategySelector.get_versions_for_strategy(strategy_dto.id)

        data = []
        for v in versions_data:
            data.append({
                'id': v['id'],
                'strategy_id': v['strategy_id'],
                'version': v['version_number'],
                'string': v['final_search_string'],
                'total_found': v['total_found'],
                'status': v.get('status', 'DRAFT'),
                'justification': v.get('justification', ''),
                'date': v['created_at'].strftime("%Y-%m-%d %H:%M")
            })

        return JsonResponse({'versions': data})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@project_member_required
def search_results_view(request, project_id, strategy_id, project):
    try:
        # Use Selector to get DTO
        strategy_dto = SearchStrategySelector.get_by_id(strategy_id)
        if not strategy_dto:
            raise Http404("Strategy not found")

        results_dto = search_strategy_service.get_search_results_dto(strategy_id)
        year_filter = request.GET.get('year')
        studies = getattr(results_dto, 'studies', []) if results_dto else []

        if year_filter and studies:
            studies = [s for s in studies if str(s.get('year')) == year_filter]

        context = {
            'project': project,
            'strategy': strategy_dto,  # Passing DTO instead of Model
            'results': results_dto,
            'studies': studies,
            'years_range': range(2025, 2000, -1),
            'current_year_filter': year_filter,
            'timeline_stages': DesignPhaseSelector.get_design_timeline_context(project.id)
        }
        return render(request, 'search_results.html', context)
    except Exception as e:
        raise Http404(f"Strategy not found or error: {str(e)}")


@project_member_required
@require_POST
def approve_strategy(request, project_id, strategy_id, project):
    try:
        justification = request.POST.get('justification')
        if not justification or not justification.strip():
            messages.error(request, "Justification is required for approval.", extra_tags='design')
            return redirect(request.META.get('HTTP_REFERER', '/'))

        strategy = search_strategy_service.change_strategy_status(
            strategy_id,
            SearchStrategy.Status.APPROVED,
            request.user,
            justification=justification
        )
        messages.success(request, f"Strategy approved successfully!", extra_tags='design')
        return redirect(build_design_url(project_id, 'strategies/'))
    except Exception as e:
        messages.error(request, str(e), extra_tags='design')
        return redirect(request.META.get('HTTP_REFERER', '/'))


@project_member_required
@require_POST
def reject_strategy(request, project_id, strategy_id, project):
    try:
        justification = request.POST.get('justification')
        if not justification or not justification.strip():
            messages.error(request, "Justification is required for rejection.", extra_tags='design')
            return redirect(request.META.get('HTTP_REFERER', '/'))

        strategy = search_strategy_service.change_strategy_status(
            strategy_id,
            SearchStrategy.Status.REJECTED,
            request.user,
            justification=justification
        )
        messages.warning(request, "Strategy rejected.", extra_tags='design')
        return redirect(build_design_url(project_id, 'strategies/'))
    except Exception as e:
        messages.error(request, str(e), extra_tags='design')
        return redirect(request.META.get('HTTP_REFERER', '/'))


@project_member_required
@require_POST
def delete_strategy_version(request, project_id, version_id, project):
    try:
        search_strategy_service.delete_strategy_version(version_id)
        return JsonResponse({'status': 'success', 'message': 'Version deleted successfully'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@project_member_required
@require_POST
def consolidate_search_strategy_stage_view(request, project_id, project):
    try:
        if project.owner != request.user:
            messages.error(request, "Only the project owner can consolidate the stage.", extra_tags='design')
            return redirect(build_design_url(project_id, 'strategies/'))

        design_phase_service.consolidate_search_strategy_stage(project_id, request.user)
        messages.success(request, "Stage consolidated successfully! Design Phase is now Finalized.", extra_tags='design')

        return redirect('design:dashboard', project_id=project_id)

    except Exception as e:
        messages.error(request, f"Error consolidating stage: {str(e)}", extra_tags='design')
        return redirect(build_design_url(project_id, 'strategies/'))
