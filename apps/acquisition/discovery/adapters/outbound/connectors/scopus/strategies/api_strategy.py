"""API-based search strategy for Scopus.

This module implements the search strategy that uses Elsevier's Scopus API
for retrieving search results.
"""

import logging
import time
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from .search_strategy import SearchStrategy
from apps.acquisition.discovery.infrastructure.http import HttpClient
from apps.acquisition.discovery.infrastructure.normalization import ScopusResultNormalizer

logger = logging.getLogger(__name__)


class ScopusApiStrategy(SearchStrategy):
    """Search strategy using Scopus/Elsevier API.
    
    This strategy uses the official Elsevier API to retrieve results.
    It's the preferred method when available as it provides structured data.
    
    Features:
    - Pagination support for large result sets
    - Automatic retry on transient failures (via HttpClient)
    - Parallel abstract fetching for better performance
    - Result normalization to standard format
    
    Attributes:
        http_client: HTTP client with retry logic
        normalizer: Result normalizer for Scopus data
        api_key: Elsevier API key
        base_url: Base URL for Elsevier API
    """
    
    def __init__(
        self,
        http_client: HttpClient,
        normalizer: ScopusResultNormalizer,
        api_key: str,
        base_url: str = "https://api.elsevier.com"
    ):
        """Initialize Scopus API strategy.
        
        Args:
            http_client: HTTP client for making requests
            normalizer: Normalizer for Scopus results
            api_key: Elsevier API key
            base_url: Base URL for Elsevier API
        """
        self.http_client = http_client
        self.normalizer = normalizer
        self.api_key = api_key
        self.base_url = base_url
        
        # Set API key in headers
        if api_key:
            self.http_client.session.headers['X-ELS-APIKey'] = api_key
    
    def can_execute(self) -> bool:
        """Check if Scopus API is accessible.
        
        Performs a quick test request to verify API availability.
        
        Returns:
            True if API is accessible, False otherwise
        """
        if not self.api_key:
            logger.debug("Scopus API cannot execute: missing API key")
            return False
        
        try:
            # Quick test with minimal payload
            test_url = f"{self.base_url}/content/search/scopus"
            response = self.http_client.get(
                test_url,
                params={'query': 'TITLE(test)', 'count': 1},
                timeout=5
            )
            
            # API is accessible if we get any response (200, 400, 401)
            return response.status_code in [200, 400, 401]
            
        except Exception as e:
            logger.debug(f"Scopus API not accessible: {e}")
            return False
    
    def execute(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Execute search using Scopus API.
        
        Performs paginated search through the Scopus API and normalizes results.
        
        Args:
            query: Search query string (can be Scopus query syntax)
            max_results: Maximum number of results to return
            
        Returns:
            List of normalized result dictionaries
            
        Raises:
            Exception: If API requests fail
        """
        logger.info(f"Executing Scopus API search: '{query}' (max: {max_results})")
        
        results = []
        start = 0
        count = min(max_results, 25)  # Scopus API limit per request
        
        # Format query for Scopus
        if query.strip().startswith("TITLE-ABS-KEY"):
            scopus_query = query
        else:
            scopus_query = f"TITLE-ABS-KEY({query})"
        
        while len(results) < max_results:
            # Build request parameters
            params = {
                'query': scopus_query,
                'start': start,
                'count': count,
                'view': 'COMPLETE'
            }
            
            logger.debug(f"Fetching Scopus results: start={start}, count={count}")
            
            # Make request
            url = f"{self.base_url}/content/search/scopus"
            response = self.http_client.get(url, params=params, timeout=30)
            
            # Handle rate limiting
            if response.status_code == 429:
                raise Exception("Scopus API quota exceeded")
            
            # Handle authentication errors
            if response.status_code == 401:
                raise Exception("Invalid Scopus API key")
            
            response.raise_for_status()
            data = response.json()
            
            # Extract results
            search_results = data.get('search-results', {})
            entries = search_results.get('entry', [])
            total_results = int(search_results.get('opensearch:totalResults', 0))
            
            logger.info(
                f"Scopus API returned {len(entries)} results "
                f"(total available: {total_results})"
            )
            
            if not entries:
                break
            
            # Identify entries without abstracts
            entries_without_abstract = []
            for entry in entries:
                if not entry.get('dc:description'):
                    identifier = entry.get('dc:identifier', '')
                    if identifier.startswith('SCOPUS_ID:'):
                        sid = identifier.replace('SCOPUS_ID:', '')
                        entries_without_abstract.append((entry, sid))
            
            # Fetch missing abstracts in parallel
            abstracts_map = {}
            if entries_without_abstract:
                scopus_ids = [sid for _, sid in entries_without_abstract]
                abstracts_map = self._fetch_abstracts_parallel(scopus_ids)
            
            # Normalize and collect results
            for entry in entries:
                if len(results) >= max_results:
                    break
                
                # Get abstract from entry or fetched map
                identifier = entry.get('dc:identifier', '')
                sid = identifier.replace('SCOPUS_ID:', '') if identifier.startswith('SCOPUS_ID:') else ''
                abstract = entry.get('dc:description') or abstracts_map.get(sid)
                
                # Normalize result
                normalized = self.normalizer.normalize(entry, abstract)
                results.append(normalized)
            
            # Check if we should continue pagination
            if len(entries) < count or len(results) >= total_results:
                break
            
            start += count
            time.sleep(0.5)  # Small delay between pages
        
        logger.info(f"Scopus API search completed: {len(results)} results")
        return results
    
    def _fetch_abstracts_parallel(self, scopus_ids: List[str]) -> Dict[str, str]:
        """Fetch abstracts in parallel using ThreadPoolExecutor.
        
        Args:
            scopus_ids: List of Scopus IDs to fetch abstracts for
            
        Returns:
            Dictionary mapping Scopus ID to abstract text
        """
        abstracts_map = {}
        
        if not scopus_ids:
            return abstracts_map
        
        # Limit to first 10 to avoid excessive requests
        max_abstracts = min(len(scopus_ids), 10)
        ids_to_fetch = scopus_ids[:max_abstracts]
        
        with ThreadPoolExecutor(max_workers=min(5, len(ids_to_fetch))) as executor:
            future_to_id = {
                executor.submit(self._fetch_single_abstract, sid): sid
                for sid in ids_to_fetch
            }
            
            for future in as_completed(future_to_id):
                sid = future_to_id[future]
                try:
                    abstract = future.result()
                    if abstract:
                        abstracts_map[sid] = abstract
                except Exception as e:
                    logger.debug(f"Failed to fetch abstract for {sid}: {e}")
        
        return abstracts_map
    
    def _fetch_single_abstract(self, scopus_id: str) -> str:
        """Fetch abstract for a single document.
        
        Args:
            scopus_id: Scopus ID of the document
            
        Returns:
            Abstract text or empty string if not found
        """
        url = f"{self.base_url}/content/abstract/scopus_id/{scopus_id}"
        
        try:
            response = self.http_client.get(url, timeout=15)
            
            if not response.ok:
                return ""
            
            data = response.json()
            coredata = data.get('abstracts-retrieval-response', {}).get('coredata', {})
            abstract = coredata.get('dc:description', '')
            
            return abstract.strip() if abstract else ""
            
        except Exception as e:
            logger.debug(f"Error fetching abstract for {scopus_id}: {e}")
            return ""
