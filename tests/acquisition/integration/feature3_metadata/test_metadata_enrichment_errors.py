"""
Tests de errores para Feature 3 (Consolidación de metadatos).

Verifican tolerancia a fallos por estudio y normalización de DOI.
"""
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.acquisition.metadata.application.consolidation_service import (
    ConsolidationService,
)
from apps.acquisition.metadata.domain.value_objects.consolidation_status import (
    ConsolidationStatus,
)
from apps.acquisition.metadata.domain.services.metadata_normalizer import (
    MetadataNormalizer,
)
from apps.acquisition.shared.domain.entities.study import Study


class ExplodingNormalizer(MetadataNormalizer):
    def __init__(self, failing_titles: set[str]):
        super().__init__()
        self.failing_titles = failing_titles

    def normalize(self, study: Study) -> Study:
        if study.title in self.failing_titles:
            raise RuntimeError("Normalization failed")
        return super().normalize(study)


def test_consolidation_continues_when_one_study_fails():
    service = ConsolidationService(connectors={})
    service.normalizer = ExplodingNormalizer({"Failing Study"})

    studies = [
        Study.from_dict(
            {
                "title": "Healthy Study A",
                "link": "https://example.com/a",
                "source": "Manual",
                "doi": "10.1000/healthy.a",
                "year": 2024,
                "authors": ["Tester A"],
            }
        ),
        Study.from_dict(
            {
                "title": "Failing Study",
                "link": "https://example.com/failing",
                "source": "Manual",
                "doi": "10.1000/failing",
                "year": 2024,
                "authors": ["Tester B"],
            }
        ),
        Study.from_dict(
            {
                "title": "Healthy Study B",
                "link": "https://example.com/b",
                "source": "Manual",
                "doi": "10.1000/healthy.b",
                "year": 2024,
                "authors": ["Tester C"],
            }
        ),
    ]

    result = service.consolidate(studies)

    status_by_title = {study.title: study.consolidation_status for study in result.studies}

    assert len(result.studies) == 3
    assert status_by_title["Failing Study"] == ConsolidationStatus.FALLIDO.value
    assert result.summary["failed"] == 1
    assert status_by_title["Healthy Study A"] == ConsolidationStatus.COMPLETO.value
    assert status_by_title["Healthy Study B"] == ConsolidationStatus.COMPLETO.value


def test_consolidation_normalizes_prefixed_doi():
    study = Study.from_dict(
        {
            "title": "Prefixed DOI",
            "link": "https://example.com/prefixed",
            "source": "Manual",
            "doi": "https://doi.org/10.1016/j.infsof.2008.01.006",
            "year": 2008,
            "authors": ["Tester"],
        }
    )

    service = ConsolidationService(connectors={})
    result = service.consolidate([study])

    normalized = result.studies[0]
    assert normalized.doi is not None
    assert not normalized.doi.value.startswith("http")
    assert normalized.doi.value == "10.1016/j.infsof.2008.01.006"


def test_consolidation_rejects_invalid_doi():
    with pytest.raises(ValueError):
        Study.from_dict(
            {
                "title": "Invalid DOI Study",
                "link": "https://example.com/invalid",
                "source": "Manual",
                "doi": "asdasd",
                "year": 2024,
                "authors": ["Tester"],
            }
        )
