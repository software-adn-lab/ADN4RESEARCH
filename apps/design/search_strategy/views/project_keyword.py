from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
# REFACTORED: Import decorator from shared module
from apps.shared.decorators import project_member_required
from apps.design.search_strategy.models.keyword import ProjectKeyword
from apps.design.search_strategy.services.search_strategy_service import SearchStrategyService

search_strategy_service = SearchStrategyService()


@project_member_required
@require_POST
def create_project_keyword(request, project_id, project_dto):
    """
    Create a new project keyword.

    CHANGED: project parameter is now project_dto (dict from IProjectManagement)
    """
    try:
        term = request.POST.get('term', '').strip()
        synonyms = request.POST.get('synonyms', '').strip()

        if not term:
            return JsonResponse({'error': 'Key term cannot be empty.'}, status=400)

        keyword = search_strategy_service.get_or_create_project_keyword(project_id, term, synonyms)
        return JsonResponse({'status': 'success', 'keyword_id': keyword.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@project_member_required
@require_POST
def update_project_keyword(request, project_id, keyword_id, project_dto):
    """
    Update an existing project keyword.

    CHANGED: project parameter is now project_dto (dict from IProjectManagement)
    """
    try:
        keyword = get_object_or_404(ProjectKeyword, id=keyword_id)
        term = request.POST.get('term', '').strip()
        synonyms = request.POST.get('synonyms', '').strip()

        if not term:
            return JsonResponse({'error': 'Key term cannot be empty.'}, status=400)

        keyword.term = term
        keyword.synonyms = synonyms
        keyword.save()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@project_member_required
@require_POST
def delete_project_keyword(request, project_id, keyword_id, project_dto):
    """
    Delete a project keyword.

    CHANGED: project parameter is now project_dto (dict from IProjectManagement)
    """
    try:
        keyword = get_object_or_404(ProjectKeyword, id=keyword_id)
        keyword.delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
