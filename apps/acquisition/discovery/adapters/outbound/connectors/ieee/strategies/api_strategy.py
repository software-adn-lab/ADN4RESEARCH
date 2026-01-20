"""API-based search strategy for IEEE Xplore.

This module implements the search strategy that uses IEEE's REST API
(/rest/search endpoint) for retrieving search results.
"""

import logging
from typing import List, Dict, Any
import requests

from .search_strategy import SearchStrategy, SearchResult
from apps.acquisition.discovery.infrastructure.http import HttpClient
from apps.acquisition.discovery.infrastructure.normalization import IeeeResultNormalizer

logger = logging.getLogger(__name__)


class IeeeApiStrategy(SearchStrategy):
    """Search strategy using IEEE Xplore REST API.
    
    This strategy uses the /rest/search endpoint to retrieve results in JSON format.
    It's the preferred method when available as it's faster and more reliable than
    web scraping.
    
    Features:
    - Pagination support for large result sets
    - Automatic retry on transient failures (via HttpClient)
    - Result normalization to standard format
    
    Attributes:
        http_client: HTTP client with retry logic
        normalizer: Result normalizer for IEEE data
        api_url: Base URL for IEEE API (via proxy or direct)
        test_url: URL for checking API availability
    """
    
    def __init__(
        self,
        http_client: HttpClient,
        normalizer: IeeeResultNormalizer,
        api_url: str = None,
        test_url: str = None
    ):
        """Initialize IEEE API strategy.
        
        Args:
            http_client: HTTP client for making requests
            normalizer: Normalizer for IEEE results
            api_url: URL for search API (uses default if None)
            test_url: URL for testing API availability (uses default if None)
        """
        self.http_client = http_client
        self.normalizer = normalizer
        self.api_url = api_url or "https://bvirtual.epn.edu.ec:2097/rest/search"
        self.test_url = test_url or "https://ieeexplore.ieee.org/rest/search"
    
    def can_execute(self) -> bool:
        """Check if IEEE API is accessible.
        
        Performs a quick test request to verify API availability.
        This helps determine if we're on campus/VPN or if the API
        is reachable.
        
        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Quick test with minimal payload
            response = self.http_client.get(
                self.test_url,
                timeout=5
            )
            
            # API is accessible if we get any response (200, 400, 401)
            # 400/401 means API is there but we need proper auth/params
            return response.status_code in [200, 400, 401]
            
        except Exception as e:
            logger.debug(f"IEEE API not accessible: {e}")
            return False
    
    def execute(self, query: str, max_results: int) -> SearchResult:
        """Execute search using IEEE REST API.
        
        Performs paginated search through the IEEE API and normalizes results.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            SearchResult with results list and total_available count
            
        Raises:
            requests.RequestException: If API requests fail
            ValueError: If API returns non-JSON response
        """
        logger.info(f"Executing IEEE API search: '{query}' (max: {max_results})")
        
        # Track total available (thread-safe: local variable, not instance state)
        total_available: int | None = None
        
        results = []
        page_size = min(max_results, 100)
        page_number = 1
        
        while len(results) < max_results:
            # Build request payload
            payload = {
                "queryText": query,
                "highlight": False,
                "returnFacets": ["ALL"],
                "returnType": "SEARCH",
                "matchPubs": True,
                "pageNumber": page_number,
                "rowsPerPage": page_size
            }
            
            logger.debug(f"Fetching page {page_number} from IEEE API")
            
            # Make request
            response = self.http_client.post(
                self.api_url,
                json=payload,
                timeout=30
            )
            
            # Check for redirect (session expired)
            if response.status_code in (301, 302, 303, 307, 308, 401):
                logger.warning(
                    f"Session invalid ({response.status_code}). "
                    "API strategy cannot re-authenticate."
                )
                raise ValueError("Session expired, re-authentication needed")
            
            # Verify JSON response
            content_type = response.headers.get("Content-Type", "")
            if "application/json" not in content_type.lower():
                logger.error(
                    f"IEEE API returned non-JSON response. "
                    f"Status: {response.status_code}, "
                    f"Content-Type: {content_type}"
                )
                raise ValueError("IEEE API returned non-JSON response")
            
            response.raise_for_status()
            data = response.json()
            
            # Extract records
            records = data.get('records', [])
            total_records = data.get('totalRecords', 0)
            
            # Store total available (from API) - only on first page
            if total_available is None:
                total_available = total_records
            
            logger.info(
                f"Page {page_number}: {len(records)} results "
                f"(total available: {total_records})"
            )
            
            if not records:
                break
            
            # Normalize and collect results
            for record in records:
                if len(results) >= max_results:
                    break
                
                normalized = self.normalizer.normalize(record)
                results.append(normalized)
            
            # Check if we should continue pagination
            if len(records) < page_size or len(results) >= total_records:
                break
            
            page_number += 1
        
        logger.info(f"IEEE API search completed: {len(results)} results")
        return SearchResult(results=results, total_available=total_available)
