"""Task wrappers that call the orchestrator (scaffold).

In production these would be Celery tasks; for now they are plain functions
which can be invoked synchronously in tests.
"""

from apps.acquisition.components.search_orchestrator.orchestrator import SearchOrchestrator
from apps.acquisition.domain.entities.search_strategy import SearchStrategy


def perform_search(orchestrator: SearchOrchestrator, strategy: SearchStrategy) -> None:
    orchestrator.request_search(strategy)
