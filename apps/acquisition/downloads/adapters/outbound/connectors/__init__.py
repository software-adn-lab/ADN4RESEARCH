"""Conectores a fuentes externas para descarga de PDFs."""

from .unpaywall_checker import UnpaywallChecker
from .http_downloader import HttpDownloader
from .alternative_source_finder import AlternativeSourceFinder

__all__ = [
    "UnpaywallChecker",
    "HttpDownloader",
    "AlternativeSourceFinder",
]
