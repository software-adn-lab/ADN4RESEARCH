"""
Celery tasks for discovery operations.

In production these would be Celery tasks (@shared_task or @app.task);
for now they are plain functions which can be invoked synchronously in tests.

Future integration:
    from celery import shared_task

    @shared_task
    def perform_discovery_async(strategy_id: str, translation_statuses: dict, supported_sources: list[str]):
        ...
"""

from apps.acquisition.discovery.application.discovery_service import DiscoveryService
from apps.acquisition.discovery.domain.entities.discovery_result import DiscoveryResult


def perform_discovery(
    service: DiscoveryService,
    strategy_id: str,
    translation_statuses: dict,
    supported_sources: list[str]
) -> DiscoveryResult:
    """
    Execute discovery process synchronously.

    Args:
        service: DiscoveryService instance with injected connectors
        strategy_id: ID of the search strategy
        translation_statuses: Translation status per source
        supported_sources: List of supported sources

    Returns:
        DiscoveryResult with studies and summary

    Example:
        >>> from apps.acquisition.discovery.api import DiscoveryService
        >>> from apps.acquisition.shared.testing.mocks import MockScopusConnector, MockIeeeConnector
        >>>
        >>> connectors = {
        ...     "Scopus": MockScopusConnector(),
        ...     "IEEE Xplore": MockIeeeConnector()
        ... }
        >>> service = DiscoveryService(connectors=connectors)
        >>>
        >>> result = perform_discovery(
        ...     service=service,
        ...     strategy_id="norm-001",
        ...     translation_statuses={
        ...         "Scopus": {"status": "ready", "query": "TITLE-ABS-KEY(...)"},
        ...         "IEEE Xplore": {"status": "ready", "query": "..."}
        ...     },
        ...     supported_sources=["Scopus", "IEEE Xplore"]
        ... )
    """
    return service.execute(
        strategy_id=strategy_id,
        translation_statuses=translation_statuses,
        supported_sources=supported_sources
    )
