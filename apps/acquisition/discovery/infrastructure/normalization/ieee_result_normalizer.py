"""IEEE Xplore result normalizer.

This module extracts and encapsulates the normalization logic for IEEE Xplore
API responses, converting them to the standard format expected by the application.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

from .result_normalizer import ResultNormalizer

logger = logging.getLogger(__name__)


class IeeeResultNormalizer(ResultNormalizer):
    """Normalizes IEEE Xplore API results to standard format.
    
    This class handles the conversion of IEEE Xplore's specific data structure
    (from the /rest/search endpoint) into the standardized format used throughout
    the application.
    
    IEEE-specific handling:
    - Extracts article number for link construction
    - Handles multiple author name formats (preferredName, fullName, etc.)
    - Infers open access status from multiple possible fields
    - Constructs PDF URLs when available
    """
    
    def normalize(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize an IEEE Xplore record to standard format.
        
        Args:
            record: Raw record from IEEE Xplore /rest/search endpoint
            
        Returns:
            Normalized result dictionary with standard fields:
            - title: Article title
            - link: URL to the article on IEEE Xplore
            - doi: Digital Object Identifier (if available)
            - source: Always 'IEEE Xplore'
            - year: Publication year (if available)
            - authors: List of author names
            - abstract: Article abstract (if available)
            - is_open_access: Open access status (if determinable)
            - pdf_url: Direct PDF link (if available)
            
        Raises:
            ValueError: If required fields are missing
        """
        article_number = record.get('articleNumber', '')
        
        # Extract access information
        is_open_access, pdf_url = self._extract_access_info(record, article_number)
        
        # Build normalized result
        result = {
            'title': record.get('articleTitle', 'N/A'),
            'link': f"https://ieeexplore.ieee.org/document/{article_number}" if article_number else '',
            'doi': record.get('doi'),
            'source': 'IEEE Xplore',
            'year': record.get('publicationYear'),
            'authors': self._extract_authors(record.get('authors', [])),
            'abstract': self._extract_abstract(record),
            'is_open_access': is_open_access,
            'pdf_url': pdf_url,
        }
        
        # Validate the normalized result
        self._validate_normalized_result(result)
        
        return result
    
    def _extract_authors(self, authors_data: List[Any]) -> List[str]:
        """Extract author names from IEEE's author data structure.
        
        IEEE provides author information in various formats. This method
        tries multiple fields to extract the best available name.
        
        Args:
            authors_data: List of author objects from IEEE API
            
        Returns:
            List of author name strings
        """
        if not authors_data:
            return []
        
        author_names = []
        
        for author in authors_data:
            if isinstance(author, dict):
                # Try multiple name fields in order of preference
                name = (
                    author.get('preferredName') or
                    author.get('fullName') or
                    author.get('name') or
                    author.get('normalizedName', '')
                )
                if name:
                    author_names.append(name)
            elif isinstance(author, str):
                # Sometimes authors are just strings
                author_names.append(author)
        
        return author_names
    
    def _extract_abstract(self, record: Dict[str, Any]) -> Optional[str]:
        """Extract and clean abstract from record.
        
        IEEE's API returns abstracts with highlight markers when highlight=True
        in the request payload. These markers look like [::term::] and need to
        be removed for clean display.
        
        Args:
            record: IEEE record dictionary
            
        Returns:
            Cleaned abstract string or None if not available
        """
        import re
        
        abstract = record.get('abstract', '')
        
        if not abstract:
            return None
        
        # Remove IEEE highlight markers [::text::]
        cleaned = re.sub(r'\[::', '', abstract)
        cleaned = re.sub(r'::\]', '', cleaned)
        
        # Normalize whitespace (multiple spaces to single)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        cleaned = cleaned.strip()
        return cleaned if cleaned else None
    
    def _extract_access_info(
        self,
        record: Dict[str, Any],
        article_number: str
    ) -> Tuple[Optional[bool], Optional[str]]:
        """Infer open access status and PDF URL from record.
        
        IEEE provides access information in multiple fields with varying
        formats. This method attempts to extract the most accurate information
        by checking multiple sources.
        
        Args:
            record: IEEE record dictionary
            article_number: Article number for URL construction
            
        Returns:
            Tuple of (is_open_access, pdf_url)
            - is_open_access: True/False/None if status can/cannot be determined
            - pdf_url: Direct PDF URL or None if not available
        """
        is_open_access: Optional[bool] = None
        
        # Check multiple possible open access flag fields
        flag_fields = ["openAccessFlag", "isOa", "openAccess", "isOpenAccess"]
        for field in flag_fields:
            if field in record:
                value = record.get(field)
                
                if isinstance(value, str):
                    # Handle string values
                    normalized = value.lower()
                    if "open" in normalized:
                        is_open_access = True
                    elif any(k in normalized for k in ("denied", "closed", "subscription")):
                        is_open_access = False
                else:
                    # Handle boolean values
                    is_open_access = bool(value) if value is not None else None
                
                if is_open_access is not None:
                    break
        
        # Check accessType field as fallback
        if is_open_access is None:
            access_type = (
                record.get("accessType") or
                record.get("accessType_s") or
                record.get("accessTypeIcon")
            )
            
            if isinstance(access_type, str):
                normalized = access_type.lower()
                if "open" in normalized:
                    is_open_access = True
                elif any(k in normalized for k in ("denied", "closed", "subscription")):
                    is_open_access = False
        
        # Extract PDF URL
        pdf_url = (
            record.get("pdfLink") or
            record.get("htmlLink") or
            record.get("fullTextLink")
        )
        
        # Handle list values
        if isinstance(pdf_url, list):
            pdf_url = pdf_url[0] if pdf_url else None
        
        # Convert relative URLs to absolute
        if pdf_url and pdf_url.startswith('/'):
            pdf_url = f"https://ieeexplore.ieee.org{pdf_url}"
        
        # Construct PDF URL for open access articles if not provided
        if not pdf_url and article_number and is_open_access:
            pdf_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={article_number}"
        
        return is_open_access, pdf_url
