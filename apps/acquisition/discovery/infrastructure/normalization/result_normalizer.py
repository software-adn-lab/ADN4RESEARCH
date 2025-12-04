"""Base class for normalizing provider-specific results to standard format.

This module provides an abstract base class that defines the contract for
result normalization across different academic sources (IEEE, Scopus, etc.).
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ResultNormalizer(ABC):
    """Base class for normalizing provider-specific results.
    
    This abstract class defines the interface that all result normalizers
    must implement. It provides a common structure for converting
    provider-specific data formats into a standardized format that
    the rest of the application can work with.
    
    The standard format includes:
    - title: str (required)
    - link: str (required)
    - doi: str | None (optional)
    - source: str (required, e.g., 'IEEE Xplore', 'Scopus')
    - year: int | None (optional)
    - authors: List[str] (optional, can be empty list)
    - abstract: str | None (optional)
    - is_open_access: bool | None (optional)
    - pdf_url: str | None (optional)
    """
    
    @abstractmethod
    def normalize(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a single result to standard format.
        
        This method must be implemented by subclasses to handle
        provider-specific data structures.
        
        Args:
            raw_result: Provider-specific result dictionary
            
        Returns:
            Normalized result dictionary with standard fields
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        pass
    
    def normalize_batch(self, raw_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize multiple results.
        
        This is a convenience method that applies normalization to
        a list of results. It handles errors gracefully by logging
        failures and continuing with the next result.
        
        Args:
            raw_results: List of provider-specific result dictionaries
            
        Returns:
            List of normalized result dictionaries
        """
        normalized = []
        
        for i, raw_result in enumerate(raw_results):
            try:
                normalized_result = self.normalize(raw_result)
                normalized.append(normalized_result)
            except Exception as e:
                logger.error(
                    f"Failed to normalize result {i}: {e}. "
                    f"Raw data: {raw_result}"
                )
                # Continue with next result instead of failing completely
                continue
        
        logger.debug(
            f"Normalized {len(normalized)}/{len(raw_results)} results successfully"
        )
        
        return normalized
    
    def _validate_normalized_result(self, result: Dict[str, Any]) -> None:
        """Validate that a normalized result has required fields.
        
        This is a helper method that subclasses can use to ensure
        their normalized results meet the minimum requirements.
        
        Args:
            result: Normalized result dictionary
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        required_fields = ['title', 'link', 'source']
        
        for field in required_fields:
            if field not in result:
                raise ValueError(f"Missing required field: {field}")
            
            if not result[field]:
                raise ValueError(f"Required field '{field}' cannot be empty")
        
        # Validate types
        if not isinstance(result['title'], str):
            raise ValueError(f"Field 'title' must be string, got {type(result['title'])}")
        
        if not isinstance(result['link'], str):
            raise ValueError(f"Field 'link' must be string, got {type(result['link'])}")
        
        if not isinstance(result['source'], str):
            raise ValueError(f"Field 'source' must be string, got {type(result['source'])}")
        
        # Validate optional fields if present
        if 'year' in result and result['year'] is not None:
            if not isinstance(result['year'], int):
                raise ValueError(f"Field 'year' must be int or None, got {type(result['year'])}")
        
        if 'authors' in result and result['authors'] is not None:
            if not isinstance(result['authors'], list):
                raise ValueError(f"Field 'authors' must be list or None, got {type(result['authors'])}")
