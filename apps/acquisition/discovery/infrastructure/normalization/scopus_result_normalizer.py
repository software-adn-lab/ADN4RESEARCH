"""Scopus result normalizer.

This module extracts and encapsulates the normalization logic for Scopus
API responses, converting them to the standard format expected by the application.
"""

import logging
import re
from typing import Dict, Any, List, Optional

from .result_normalizer import ResultNormalizer

logger = logging.getLogger(__name__)


class ScopusResultNormalizer(ResultNormalizer):
    """Normalizes Scopus API results to standard format.
    
    This class handles the conversion of Scopus/Elsevier API's specific data
    structure into the standardized format used throughout the application.
    
    Scopus-specific handling:
    - Extracts EID and Scopus ID for link construction
    - Handles Dublin Core metadata fields (dc:title, dc:creator, etc.)
    - Parses publication dates to extract year
    - Infers open access status from multiple possible fields
    - Constructs DOI-based PDF URLs for open access articles
    """
    
    def normalize(self, entry: Dict[str, Any], abstract: Optional[str] = None) -> Dict[str, Any]:
        """Normalize a Scopus API entry to standard format.
        
        Args:
            entry: Raw entry from Scopus API search results
            abstract: Optional abstract text (may be fetched separately)
            
        Returns:
            Normalized result dictionary with standard fields:
            - title: Article title
            - link: URL to the article on Scopus
            - doi: Digital Object Identifier (if available)
            - source: Always 'Scopus'
            - year: Publication year (if available)
            - authors: List of author names
            - abstract: Article abstract (if available)
            - is_open_access: Open access status (if determinable)
            - pdf_url: Direct PDF link (if available)
            
        Raises:
            ValueError: If required fields are missing
        """
        # Extract basic fields
        title = entry.get('dc:title', 'N/A')
        doi = entry.get('prism:doi')
        
        # Extract year from cover date
        year = self._extract_year(entry.get('prism:coverDate', ''))
        
        # Extract authors
        authors = self._extract_authors(entry)
        
        # Extract or use provided abstract
        if abstract is None:
            abstract = entry.get('dc:description')
        
        # Clean abstract
        abstract = abstract.strip() if abstract else None
        
        # Construct link
        link = self._construct_link(entry)
        
        # Extract open access information
        is_open_access = self._extract_open_access_status(entry)
        
        # Construct PDF URL for open access articles
        pdf_url = self._construct_pdf_url(doi, is_open_access)
        
        # Build normalized result
        result = {
            'title': title,
            'link': link,
            'doi': doi,
            'source': 'Scopus',
            'year': year,
            'authors': authors,
            'abstract': abstract,
            'is_open_access': is_open_access,
            'pdf_url': pdf_url,
        }
        
        # Validate the normalized result
        self._validate_normalized_result(result)
        
        return result
    
    def _extract_year(self, cover_date: str) -> Optional[int]:
        """Extract year from Scopus cover date string.
        
        Scopus provides dates in various formats (YYYY-MM-DD, YYYY-MM, YYYY).
        This method extracts the 4-digit year using regex.
        
        Args:
            cover_date: Date string from Scopus (e.g., "2023-05-15")
            
        Returns:
            Year as integer or None if not found
        """
        if not cover_date:
            return None
        
        match = re.search(r'\d{4}', cover_date)
        if match:
            return int(match.group())
        
        return None
    
    def _extract_authors(self, entry: Dict[str, Any]) -> List[str]:
        """Extract author names from Scopus entry.
        
        Scopus typically provides the first author in the dc:creator field.
        Additional authors may be in other fields, but for consistency with
        the current implementation, we only extract the primary creator.
        
        Args:
            entry: Scopus entry dictionary
            
        Returns:
            List of author name strings
        """
        authors = []
        
        creator = entry.get('dc:creator')
        if creator:
            authors.append(creator)
        
        return authors
    
    def _construct_link(self, entry: Dict[str, Any]) -> str:
        """Construct the Scopus record URL.
        
        Scopus provides multiple identifiers (EID, Scopus ID) and sometimes
        direct links. This method tries multiple approaches to construct
        the best available link.
        
        Args:
            entry: Scopus entry dictionary
            
        Returns:
            URL to the Scopus record
        """
        link = None
        
        # Try EID first (most reliable)
        eid = entry.get('eid', '')
        if eid:
            link = f"https://www.scopus.com/record/display.uri?eid={eid}&origin=resultslist"
        
        # Try Scopus ID as fallback
        if not link:
            identifier = entry.get('dc:identifier', '')
            if identifier.startswith('SCOPUS_ID:'):
                sid = identifier.replace('SCOPUS_ID:', '')
                link = f"https://www.scopus.com/record/display.uri?origin=inward&partnerID=HzOxMe3b&scp={sid}"
        
        # Check for direct link in entry links
        for entry_link in entry.get('link', []):
            if entry_link.get('@ref') == 'scopus':
                link = entry_link.get('@href', link)
                break
        
        return link or ''
    
    def _extract_open_access_status(self, entry: Dict[str, Any]) -> Optional[bool]:
        """Extract open access status from Scopus entry.
        
        Scopus provides open access information in multiple fields with
        different formats (boolean, string "0"/"1", etc.). This method
        handles all known formats.
        
        Args:
            entry: Scopus entry dictionary
            
        Returns:
            True if open access, False if not, None if unknown
        """
        is_open_access = None
        
        # Check openaccessFlag (boolean)
        openaccess_flag = entry.get('openaccessFlag')
        if isinstance(openaccess_flag, bool):
            is_open_access = openaccess_flag
            return is_open_access
        
        # Check openaccess (string or int)
        openaccess_str = entry.get('openaccess')
        if isinstance(openaccess_str, str):
            is_open_access = openaccess_str == '1'
        elif openaccess_str in [0, 1]:
            is_open_access = bool(openaccess_str)
        
        return is_open_access
    
    def _construct_pdf_url(self, doi: Optional[str], is_open_access: Optional[bool]) -> Optional[str]:
        """Construct PDF URL for open access articles.
        
        For open access articles with a DOI, we can construct a DOI.org URL
        that typically resolves to the full text.
        
        Args:
            doi: Digital Object Identifier
            is_open_access: Whether the article is open access
            
        Returns:
            PDF URL or None if not available
        """
        if is_open_access and doi:
            return f"https://doi.org/{doi}"
        
        return None
