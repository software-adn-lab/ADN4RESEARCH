"""
Tests de errores para Feature 2 (Discovery + Deduplicación).

Usan conectores stub para simular fallos y verificar tolerancia.
"""
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.acquisition.discovery.application.discovery_service import DiscoveryService
from apps.acquisition.shared.domain.constants import (
    DISCOVERY_RESULT_PARTIAL,
    TRANSLATION_STATUS_READY,
)
from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.shared.infrastructure.circuit_breaker import CircuitBreakerOpenError


class SuccessfulConnector:
    def __init__(self, studies):
        self.studies = studies

    def search(self, query: str, max_results: int = 10):
        return self.studies


class FailingConnector:
    def __init__(self, exc: Exception):
        self.exc = exc
        self.calls = 0

    def search(self, query: str, max_results: int = 10):
        self.calls += 1
        raise self.exc


def _ready(query: str = "dummy"):
    return {"status": TRANSLATION_STATUS_READY, "query": query}


def test_discovery_continues_when_one_source_fails():
    studies_scopus = [
        Study.create_discovered(
            title="A study that works",
            link="https://scopus.example.com/ok",
            source="Scopus",
            doi="10.1000/ok.1",
        ),
        Study.create_discovered(
            title="Another study that works",
            link="https://scopus.example.com/ok2",
            source="Scopus",
            doi="10.1000/ok.2",
        ),
    ]

    connectors = {
        "Scopus": SuccessfulConnector(studies_scopus),
        "IEEE Xplore": FailingConnector(RuntimeError("Connector down")),
    }

    service = DiscoveryService(connectors=connectors)

    result = service.execute(
        strategy_id="partial-discovery",
        translation_statuses={
            "Scopus": _ready(),
            "IEEE Xplore": _ready(),
        },
        supported_sources=["Scopus", "IEEE Xplore"],
        max_results_per_source=5,
    )

    assert result.summary["resultado"] == DISCOVERY_RESULT_PARTIAL
    assert len(result.studies) == len(studies_scopus)
    assert result.summary["total_por_fuente"]["Scopus"] == len(studies_scopus)
    assert "IEEE Xplore" in result.summary["no_ejecutadas"]
    assert "connection_error" in result.summary["no_ejecutadas"]["IEEE Xplore"]


def test_discovery_handles_timeout_without_stopping_pipeline():
    connectors = {
        "Scopus": SuccessfulConnector(
            [
                Study.create_discovered(
                    title="Timeout safe",
                    link="https://scopus.example.com/safe",
                    source="Scopus",
                    doi="10.1000/safe.1",
                )
            ]
        ),
        "IEEE Xplore": FailingConnector(TimeoutError("API timed out")),
    }

    service = DiscoveryService(connectors=connectors)

    result = service.execute(
        strategy_id="timeout-discovery",
        translation_statuses={
            "Scopus": _ready(),
            "IEEE Xplore": _ready(),
        },
        supported_sources=["Scopus", "IEEE Xplore"],
        max_results_per_source=3,
    )

    assert result.summary["resultado"] == DISCOVERY_RESULT_PARTIAL
    assert result.summary["total_por_fuente"]["Scopus"] == 1
    assert "TimeoutError" in result.summary["no_ejecutadas"]["IEEE Xplore"]


def test_discovery_records_circuit_breaker_open():
    scopus_study = Study.create_discovered(
        title="Breaker safe",
        link="https://scopus.example.com/breaker",
        source="Scopus",
        doi="10.1000/breaker.safe",
    )

    failing_connector = FailingConnector(
        CircuitBreakerOpenError("Circuit open for IEEE")
    )

    connectors = {
        "Scopus": SuccessfulConnector([scopus_study]),
        "IEEE Xplore": failing_connector,
    }

    service = DiscoveryService(connectors=connectors)

    result = service.execute(
        strategy_id="breaker-discovery",
        translation_statuses={
            "Scopus": _ready(),
            "IEEE Xplore": _ready(),
        },
        supported_sources=["Scopus", "IEEE Xplore"],
        max_results_per_source=3,
    )

    assert result.summary["resultado"] == DISCOVERY_RESULT_PARTIAL
    assert "CircuitBreakerOpenError" in result.summary["no_ejecutadas"]["IEEE Xplore"]
    assert failing_connector.calls == 1
    assert len(result.studies) == 1
