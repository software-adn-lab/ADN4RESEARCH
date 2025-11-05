from abc import ABC, abstractmethod
from typing import Callable, Any


class IEventBus(ABC):
    """Simple event bus contract for domain events."""

    @abstractmethod
    def publish(self, event_name: str, payload: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, event_name: str, handler: Callable) -> None:
        raise NotImplementedError
