
from apps.design.search_strategy.services.search_strategy_service import SearchStrategyService
from apps.design.research_question.services.question_services import ResearchQuestionService
from django.http import JsonResponse

search_strategy_service = SearchStrategyService()
research_question_service = ResearchQuestionService()

def generate_and_save_search_string_for_question(request, question_id):
    question = research_question_service.get_research_question_by_id(question_id, request.user)
    strategy =  search_strategy_service.get_strategy_for_question(question_id=question.id)
    if not strategy:
        return JsonResponse({'error': 'No search strategy found for this question.'}, status=404)
    try:
        updated_strategy = search_strategy_service.generate_and_save_search_string(
            strategy_id=strategy.id, 
            user_id=request.user.id
        )
        
        return JsonResponse({
            'status': 'success',
            'strategy_name': updated_strategy.name,
            'final_search_string': updated_strategy.final_search_string
        })
    except Exception as e:
        print(f"Error interno: {e}") 
        return JsonResponse({'error': str(e)}, status=500)