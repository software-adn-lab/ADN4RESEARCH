"""
Tests de errores para Feature 1 (Traducción de estrategias).

Validan que el servicio aplique controles de entrada y targets soportados.
"""
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.acquisition.shared.domain.exceptions import DomainValidationError
from apps.acquisition.translation.application.exceptions import InvalidTargetError
from apps.acquisition.translation.application.translation_service import TranslationService
from apps.acquisition.translation.domain.models import NormalizedStrategy


def _build_valid_strategy() -> NormalizedStrategy:
    return NormalizedStrategy.from_dict(
        {
            "strategy_id": "errors-translation",
            "main_terms": [
                {"term": "machine learning", "synonyms": ["deep learning"]},
                {"term": "software engineering"},
            ],
            "exclusions": ["gaming"],
            "filters": {"year": {"from": 2020, "to": 2024}},
        }
    )


def test_translation_rejects_invalid_target():
    service = TranslationService()
    strategy = _build_valid_strategy()

    with pytest.raises(InvalidTargetError):
        service.translate(strategy, "GoogleScholar")


def test_translation_requires_at_least_one_main_term():
    with pytest.raises(DomainValidationError):
        NormalizedStrategy.from_dict(
            {
                "strategy_id": "no-terms",
                "main_terms": [],
            }
        )


def test_translation_rejects_blank_terms():
    with pytest.raises(DomainValidationError):
        NormalizedStrategy.from_dict(
            {
                "strategy_id": "blank-term",
                "main_terms": [{"term": "   ", "synonyms": []}],
            }
        )
