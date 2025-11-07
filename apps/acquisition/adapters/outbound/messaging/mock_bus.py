from .event_bus import EventBus


class MockBus(EventBus):
    """Alias for the in-memory bus used in tests and early dev.

    Keeps the same in-process behavior; exists to explicitely inject a mock
    in places where a real broker will be used later.
    """

    pass
