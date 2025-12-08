"""IEEE Xplore connector module.

This module exports only the main IeeeConnector facade.
Internal implementation details (scraper, strategies) are not exposed.
"""
from .connector import IeeeConnector

__all__ = ['IeeeConnector']
