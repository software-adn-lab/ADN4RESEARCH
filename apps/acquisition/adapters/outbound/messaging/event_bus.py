from typing import Callable, Dict, List, Any


class EventBus:
    """Minimal in-process event bus used in FASE 1 for orchestration and tests."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable[[Any], None]]] = {}

    def publish(self, event_name: str, payload: Any) -> None:
        for handler in self._handlers.get(event_name, []):
            handler(payload)

    def subscribe(self, event_name: str, handler: Callable[[Any], None]) -> None:
        self._handlers.setdefault(event_name, []).append(handler)
