"""Abstract search strategy interface for Scopus.

This module defines the contract that all Scopus search strategies must implement,
enabling the Strategy pattern for flexible search execution.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result of a search operation (thread-safe, no mutable state).
    
    Attributes:
        results: List of normalized result dictionaries
        total_available: Total results available in the API (None if not provided)
    """
    results: List[Dict[str, Any]]
    total_available: Optional[int] = None


class SearchStrategy(ABC):
    """Abstract base class for Scopus search strategies.
    
    This interface defines the contract for different search execution
    strategies (API-based, web scraping, etc.). Each strategy encapsulates
    a specific way to search Scopus.
    
    The Strategy pattern allows the ScopusConnector to:
    - Switch between different search methods dynamically
    - Add new search strategies without modifying existing code
    - Test strategies independently
    - Select the best available strategy at runtime
    
    Note:
        execute() returns a SearchResult dataclass to avoid mutable state
        that could cause race conditions in concurrent environments.
    """
    
    @abstractmethod
    def can_execute(self) -> bool:
        """Check if this strategy is available and can be executed.
        
        This method should perform a quick check to determine if the
        strategy can be used. For example:
        - API strategy: Check if API is accessible
        - Web strategy: Check if credentials are available
        
        Returns:
            True if the strategy can be executed, False otherwise
        """
        pass
    
    @abstractmethod
    def execute(self, query: str, max_results: int) -> SearchResult:
        """Execute the search using this strategy.
        
        This method performs the actual search and returns normalized results.
        It should handle all strategy-specific logic including:
        - Authentication (if needed)
        - Request execution
        - Result normalization
        - Error handling
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            SearchResult with results list and total_available count
            
        Raises:
            Exception: If the search fails for any reason
        """
        pass
