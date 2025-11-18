
from apps.design.search_strategy.services.search_strategy_service import SearchStrategyService
from django.shortcuts import get_object_or_404
from apps.design.research_question.models.research_question import ResearchQuestion
from django.http import JsonResponse

search_strategy_service = SearchStrategyService()

def generate_and_save_search_string_for_question(request, project_id, question_id):
    question = get_object_or_404(ResearchQuestion, id=question_id, project__id=project_id)
    strategy =  search_strategy_service.get_strategy_for_question(question)
    if not strategy:
        return JsonResponse({'error': 'No search strategy found for this question.'}, status=404)
    updated_strategy = search_strategy_service.generate_and_save_search_string(strategy)
    return JsonResponse({
        'status': 'success',
        'strategy_name': updated_strategy.name,
        'final_search_string': updated_strategy.final_search_string
    })