"""Real connectors for academic sources (IEEE, Scopus, etc.)."""

from .ieee_connector import IeeeConnector
from .ieee_playwright_connector import IeeePlaywrightConnector
from .scopus_connector import ScopusConnector
from .scopus_playwright_connector import ScopusPlaywrightConnector

__all__ = [
    'IeeeConnector',
    'IeeePlaywrightConnector',
    'ScopusConnector',
    'ScopusPlaywrightConnector',
]
