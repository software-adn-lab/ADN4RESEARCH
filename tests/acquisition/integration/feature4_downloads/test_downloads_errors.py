"""
Tests de errores para Feature 4 (Descargas / Texto completo).

Usan mocks ligeros para simular PDFs corruptos, cascada a Sci-Hub y
marcado como no disponible.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.acquisition.downloads.application.fulltext_service import FullTextService
from apps.acquisition.downloads.domain.value_objects.download_status import DownloadStatus
from apps.acquisition.downloads.domain.value_objects.pdf_source import PdfSource
from apps.acquisition.shared.domain.entities.study import Study


def _build_service(
    *,
    oa_is_oa: bool,
    oa_info: dict | None,
    download_path: str | None,
    alternative_path: str | None,
    pdf_valid: bool,
) -> FullTextService:
    oa_checker = MagicMock()
    oa_checker.is_open_access.return_value = oa_is_oa
    oa_checker.get_oa_info.return_value = oa_info

    downloader = MagicMock()
    downloader.download_from_url.return_value = download_path

    alternative_finder = MagicMock()
    alternative_finder.find_and_download.return_value = alternative_path

    validator = MagicMock()
    validator.is_valid_pdf.return_value = pdf_valid

    return FullTextService(
        oa_checker=oa_checker,
        downloader=downloader,
        alternative_finder=alternative_finder,
        file_validator=validator,
    )


def test_download_rejects_corrupted_pdf():
    service = _build_service(
        oa_is_oa=True,
        oa_info={"is_oa": True, "pdf_url": "http://example.com/bad.pdf"},
        download_path="/tmp/corrupted.html",
        alternative_path=None,
        pdf_valid=False,
    )

    study = Study.create_discovered(
        title="Corrupted PDF",
        link="https://example.com/corrupted",
        source="Manual",
        doi="10.1000/open.access",
    )
    study.pdf_url = "http://example.com/bad.pdf"

    result = service.obtain_fulltext(study)

    assert result.download_status == DownloadStatus.NO_DISPONIBLE.value
    assert result.pdf_path is None
    assert result.pdf_source is None


def test_download_cascades_to_scihub_when_oa_fails():
    service = _build_service(
        oa_is_oa=False,
        oa_info={"is_oa": False},
        download_path=None,
        alternative_path="/tmp/downloads/alternative.pdf",
        pdf_valid=True,
    )

    study = Study.create_discovered(
        title="Needs alternative source",
        link="https://example.com/alt",
        source="Manual",
        doi="10.1000/paywall.alt",
    )

    result = service.obtain_fulltext(study)

    assert result.download_status == DownloadStatus.DISPONIBLE.value
    assert result.pdf_source == PdfSource.ALTERNATIVO.value
    assert result.pdf_path == "/tmp/downloads/alternative.pdf"


def test_download_marks_unavailable_when_all_fail():
    service = _build_service(
        oa_is_oa=False,
        oa_info={"is_oa": False},
        download_path=None,
        alternative_path=None,
        pdf_valid=True,
    )

    study = Study.create_discovered(
        title="Unavailable everywhere",
        link="https://example.com/unavailable",
        source="Manual",
        doi="10.1000/missing",
    )

    result = service.obtain_fulltext(study)

    assert result.download_status == DownloadStatus.NO_DISPONIBLE.value
    assert result.pdf_path is None
