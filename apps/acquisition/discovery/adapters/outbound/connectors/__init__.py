"""Connectors module entry point.

This module exposes only the high-level connectors for academic sources.
Internal implementation details (strategies, scrapers) are hidden within
their respective provider folders.

Public API:
- IeeeConnector: IEEE Xplore connector
- ScopusConnector: Scopus connector
- CrossrefConnector: Crossref connector

All connectors implement clean interfaces and use the Strategy pattern
internally to select between API and web scraping approaches.
"""

# Import from encapsulated provider modules
from .ieee.connector import IeeeConnector
from .scopus.connector import ScopusConnector
from .crossref.connector import CrossrefConnector

__all__ = [
    'IeeeConnector',
    'ScopusConnector',
    'CrossrefConnector',
]
