"""Web scraping search strategy for Scopus using Playwright.

This module implements the search strategy that uses Playwright for
web automation when the API is not accessible or credentials are needed.
"""

import logging
from typing import List, Dict, Any

from .search_strategy import SearchStrategy, SearchResult
from apps.acquisition.discovery.infrastructure.normalization import ScopusResultNormalizer

logger = logging.getLogger(__name__)


class ScopusWebStrategy(SearchStrategy):
    """Search strategy using Playwright web scraping.
    
    This strategy uses the existing ScopusPlaywrightConnector to perform
    searches when the API is not available. It's a fallback method that
    requires institutional credentials.
    
    Features:
    - Full browser automation via Playwright
    - EZproxy authentication handling
    - Session management
    - Result normalization to standard format
    
    Attributes:
        username: Institutional username
        password: Institutional password
        normalizer: Result normalizer for Scopus data
        headless: Whether to run browser in headless mode
    """
    
    def __init__(
        self,
        username: str,
        password: str,
        normalizer: ScopusResultNormalizer,
        headless: bool = True
    ):
        """Initialize Scopus web scraping strategy.
        
        Args:
            username: Institutional username for EZproxy
            password: Institutional password for EZproxy
            normalizer: Normalizer for Scopus results
            headless: Whether to run browser in headless mode
        """
        self.username = username
        self.password = password
        self.normalizer = normalizer
        self.headless = headless
    
    def can_execute(self) -> bool:
        """Check if credentials are available for web scraping.
        
        Web scraping requires institutional credentials to authenticate
        via EZproxy. This method simply checks if credentials were provided.
        
        Returns:
            True if credentials are available, False otherwise
        """
        has_credentials = bool(self.username and self.password)
        
        if not has_credentials:
            logger.debug("Scopus web strategy cannot execute: missing credentials")
        
        return has_credentials
    
    def execute(self, query: str, max_results: int) -> SearchResult:
        """Execute search using Playwright web scraping.
        
        This method delegates to the existing ScopusPlaywrightConnector
        which handles all the browser automation, authentication, and
        scraping logic.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            SearchResult with results list (total_available is None for web scraping)
            
        Raises:
            Exception: If web scraping fails
        """
        logger.info(f"Executing Scopus web scraping search: '{query}' (max: {max_results})")
        
        # Import here to avoid circular dependency
        from ..scraper import ScopusPlaywrightConnector
        
        # Create connector instance
        connector = ScopusPlaywrightConnector(
            username=self.username,
            password=self.password,
            headless=self.headless
        )
        
        try:
            # Execute search and collect results
            results = list(connector.search(query, max_results=max_results))
            
            logger.info(f"Scopus web scraping completed: {len(results)} results")
            # Web scraping doesn't provide total_available
            return SearchResult(results=results, total_available=None)
            
        finally:
            # Always close the connector to release browser resources
            connector.close()
