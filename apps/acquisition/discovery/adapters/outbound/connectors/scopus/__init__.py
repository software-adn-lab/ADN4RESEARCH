"""Scopus connector module.

This module exports only the main ScopusConnector facade.
Internal implementation details (scraper, strategies) are not exposed.
"""
from .connector import ScopusConnector

__all__ = ['ScopusConnector']
