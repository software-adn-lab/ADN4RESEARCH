"""Conectores a fuentes externas para descarga de PDFs."""

from .unpaywall_checker import UnpaywallChecker
from .crossref_open_access_checker import CrossrefOpenAccessChecker
from .scopus_institutional_checker import ScopusInstitutionalChecker
from .http_downloader import HttpDownloader
from .alternative_source_finder import AlternativeSourceFinder

__all__ = [
    "UnpaywallChecker",
    "CrossrefOpenAccessChecker",
    "ScopusInstitutionalChecker",
    "HttpDownloader",
    "AlternativeSourceFinder",
]
