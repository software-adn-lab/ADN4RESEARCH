from typing import List
from apps.acquisition.domain.entities.search_strategy import SearchStrategy
from apps.acquisition.adapters.outbound.messaging.event_bus import EventBus


class SearchOrchestrator:
    """Small orchestrator that emits a search requested event and collects results.

    This is a scaffold: real logic to translate queries and call connectors lives
    here in later phases.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    def request_search(self, strategy: SearchStrategy) -> None:
        # publish a domain event (scaffold)
        self.event_bus.publish("search_requested", strategy)
