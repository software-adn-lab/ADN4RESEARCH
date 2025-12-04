"""Domain layer for downloads component."""

from .interfaces import (
    IOpenAccessChecker,
    IDownloader,
    IAlternativeSourceFinder,
    IFileValidator
)
from .services import FileValidator
from .value_objects import DownloadStatus, PdfSource

__all__ = [
    # Interfaces (Ports)
    'IOpenAccessChecker',
    'IDownloader',
    'IAlternativeSourceFinder',
    'IFileValidator',
    # Services
    'FileValidator',
    # Value Objects
    'DownloadStatus',
    'PdfSource',
]
