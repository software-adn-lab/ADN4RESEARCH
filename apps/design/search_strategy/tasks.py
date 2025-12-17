import logging
from celery import shared_task
from django.contrib.auth import get_user_model
from apps.acquisition.facade import get_acquisition_facade
from apps.design.search_strategy.services.search_strategy_service import SearchStrategyService

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task
def finalize_strategy_search_task(strategy_id: int, user_id: int):
    """
    Async task to finalize the search strategy in the Acquisition module.
    This executes the search, persists results, and establishes traceability.
    """
    logger.info(f"Starting async finalization for strategy {strategy_id}")
    
    try:
        user = None
        if user_id:
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                logger.warning(f"User {user_id} not found for strategy finalization. Proceeding without user.")

        service = SearchStrategyService()
        acquisition_facade = get_acquisition_facade()

        # 1. Regenerate the full DTO (Translation + Preview)
        # We assume the strategy is already APPROVED at this point
        logger.debug(f"Generating search results DTO for strategy {strategy_id}")
        preview_result = service.get_search_results_dto(strategy_id)

        # 2. Persist in Acquisition
        logger.debug(f"Calling facade.finalize_search for strategy {strategy_id}")
        result = acquisition_facade.finalize_search(
            design_strategy_id=strategy_id,
            preview_result=preview_result,
            user=user
        )

        logger.info(f"Successfully finalized strategy {strategy_id}. "
                    f"Execution ID: {result.execution_id}, New Studies: {result.new_studies_count}")
        return {
            "strategy_id": strategy_id,
            "status": "success",
            "new_studies": result.new_studies_count
        }

    except Exception as e:
        logger.error(f"Failed to finalize strategy {strategy_id}: {str(e)}", exc_info=True)
        # We might want to re-raise to let Celery handle retries, 
        # but for now we'll just log the error to avoid infinite loops if it's a logic error.
        raise e
