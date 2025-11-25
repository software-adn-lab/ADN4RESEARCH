"""
Tests de pipeline con fallos parciales.

Simulan el flujo completo con mocks para validar tolerancia a fallos
entre Discovery, Consolidación y Descargas.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.acquisition.discovery.application.discovery_service import DiscoveryService
from apps.acquisition.metadata.application.consolidation_service import (
    ConsolidationService,
)
from apps.acquisition.metadata.domain.services.metadata_normalizer import (
    MetadataNormalizer,
)
from apps.acquisition.metadata.domain.value_objects.consolidation_status import (
    ConsolidationStatus,
)
from apps.acquisition.downloads.domain.value_objects.download_status import DownloadStatus
from apps.acquisition.shared.domain.constants import TRANSLATION_STATUS_READY
from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.shared.testing.mocks.downloads import (
    build_fulltext_service_with_mocks,
)
from apps.acquisition.shared.testing.mocks.mock_scopus_connector import (
    MockScopusConnector,
)


class ExplodingConnector:
    def __init__(self, exc: Exception):
        self.exc = exc
        self.calls = 0

    def search(self, query: str, max_results: int = 10):
        self.calls += 1
        raise self.exc


class BasicCrossrefConnector:
    def find_metadata(self, title: str, authors=None, year=None):
        return {
            "doi": "10.1000/paywall.pipeline",
            "authors": ["Auto Enriched"],
            "year": 2024,
        }


class ExplodingNormalizer(MetadataNormalizer):
    def __init__(self, failing_titles: set[str]):
        super().__init__()
        self.failing_titles = failing_titles

    def normalize(self, study: Study) -> Study:
        if study.title in self.failing_titles:
            raise RuntimeError("Enrichment failed for test")
        return super().normalize(study)


class FiveStudiesConnector:
    def search(self, query: str, max_results: int = 10):
        return [
            Study.create_discovered(
                title="OA Study",
                link="https://scopus.example.com/oa",
                source="Scopus",
                doi="10.1000/open.access",
            ),
            Study.create_discovered(
                title="Paywall Study 1",
                link="https://scopus.example.com/paywall1",
                source="Scopus",
                doi="10.1000/paywall.one",
            ),
            Study.create_discovered(
                title="Paywall Study 2",
                link="https://scopus.example.com/paywall2",
                source="Scopus",
                doi="10.1000/paywall.two",
            ),
            Study.create_discovered(
                title="Fail Study 1",
                link="https://scopus.example.com/fail1",
                source="Scopus",
                doi="10.1000/fail.one",
            ),
            Study.create_discovered(
                title="Fail Study 2",
                link="https://scopus.example.com/fail2",
                source="Scopus",
                doi="10.1000/fail.two",
            ),
        ]


def _ready(query: str = "dummy"):
    return {"status": TRANSLATION_STATUS_READY, "query": query}


def test_pipeline_continues_when_ieee_fails():
    discovery = DiscoveryService(
        connectors={
            "Scopus": MockScopusConnector(),
            "IEEE Xplore": ExplodingConnector(RuntimeError("IEEE outage")),
        }
    )

    discovery_result = discovery.execute(
        strategy_id="pipeline-ieee-down",
        translation_statuses={
            "Scopus": _ready(),
            "IEEE Xplore": _ready(),
        },
        supported_sources=["Scopus", "IEEE Xplore"],
        max_results_per_source=5,
    )

    assert discovery_result.summary["resultado"] == "partial"
    assert "IEEE Xplore" in discovery_result.summary["no_ejecutadas"]
    assert len(discovery_result.studies) > 0

    consolidation = ConsolidationService(connectors={"Crossref": BasicCrossrefConnector()})
    consolidated = consolidation.consolidate(discovery_result.studies)

    fulltext = build_fulltext_service_with_mocks()
    downloaded = [fulltext.obtain_fulltext(study) for study in consolidated.studies]

    assert len(downloaded) == len(consolidated.studies)
    assert sum(1 for study in downloaded if study.download_status == DownloadStatus.DISPONIBLE.value) >= 1


def test_pipeline_handles_partial_enrichment_failure():
    discovery = DiscoveryService(connectors={"Scopus": FiveStudiesConnector()})

    discovery_result = discovery.execute(
        strategy_id="pipeline-partial-enrichment",
        translation_statuses={"Scopus": _ready()},
        supported_sources=["Scopus"],
        max_results_per_source=10,
    )

    consolidation = ConsolidationService(connectors={})
    consolidation.normalizer = ExplodingNormalizer({"Fail Study 1", "Fail Study 2"})

    consolidated = consolidation.consolidate(discovery_result.studies)

    successful = [
        study for study in consolidated.studies
        if study.consolidation_status != ConsolidationStatus.FALLIDO.value
    ]

    assert len(successful) == 3

    fulltext = build_fulltext_service_with_mocks()
    downloaded = [fulltext.obtain_fulltext(study) for study in successful]

    assert len(downloaded) == 3
    assert all(
        study.download_status == DownloadStatus.DISPONIBLE.value
        for study in downloaded
    )
