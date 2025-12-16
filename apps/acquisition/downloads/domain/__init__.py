"""Domain layer for downloads component."""

from .interfaces import (
    IOpenAccessChecker,
    IDownloader,
    IAlternativeSourceFinder,
    IFileValidator,
    # Chain of Responsibility
    BaseOpenAccessChecker,
    OpenAccessResult,
)
from .services import FileValidator
from .value_objects import DownloadStatus, PdfSource

__all__ = [
    # Interfaces (Ports)
    'IOpenAccessChecker',
    'IDownloader',
    'IAlternativeSourceFinder',
    'IFileValidator',
    # Chain of Responsibility Base
    'BaseOpenAccessChecker',
    'OpenAccessResult',
    # Services
    'FileValidator',
    # Value Objects
    'DownloadStatus',
    'PdfSource',
]
