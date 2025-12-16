"""
Downloaders - Utilidades para descarga de PDFs.

HttpDownloader: Descarga PDFs desde URLs directas (Open Access).
SciHubDownloader: Descarga desde Sci-Hub (zona gris, configurable).
"""

from .http_downloader import HttpDownloader
from .scihub_downloader import SciHubDownloader

__all__ = [
    "HttpDownloader",
    "SciHubDownloader",
]
