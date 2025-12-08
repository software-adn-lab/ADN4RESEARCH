"""Configuration dataclasses for academic connectors.

This module provides centralized configuration for IEEE and Scopus connectors,
allowing easy customization through environment variables or direct instantiation.
"""

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class IeeeConfig:
    """Configuration for IEEE Xplore connector.
    
    This dataclass centralizes all configuration parameters for the IEEE
    connector, including URLs, timeouts, rate limits, and circuit breaker settings.
    
    Values can be loaded from environment variables or provided directly.
    
    Attributes:
        api_search_url: URL for IEEE API search (via proxy)
        api_test_url: URL for testing API availability
        web_login_url: EZproxy login URL for IEEE
        web_search_url: Web search URL (via proxy)
        success_patterns: URL/title patterns indicating successful login
        timeout: Request timeout in seconds
        rate_limit: Delay between requests in seconds
        max_retries: Maximum retry attempts for failed requests
        circuit_breaker_threshold: Failures before opening circuit
        circuit_breaker_timeout: Seconds to wait before retrying after circuit opens
        session_file: Path to session cookie file
    """
    
    # API endpoints
    api_search_url: str = field(
        default_factory=lambda: os.getenv(
            'IEEE_API_SEARCH_URL',
            'https://bvirtual.epn.edu.ec:2097/rest/search'
        )
    )
    api_test_url: str = field(
        default_factory=lambda: os.getenv(
            'IEEE_API_TEST_URL',
            'https://ieeexplore.ieee.org/rest/search'
        )
    )
    
    # Web endpoints
    web_login_url: str = field(
        default_factory=lambda: os.getenv(
            'IEEE_WEB_LOGIN_URL',
            'https://bvirtual.epn.edu.ec/login?url=http://ieeexplore.ieee.org'
        )
    )
    web_search_url: str = field(
        default_factory=lambda: os.getenv(
            'IEEE_WEB_SEARCH_URL',
            'https://bvirtual.epn.edu.ec:2097/Xplore/home.jsp'
        )
    )
    
    # Success indicators for authentication
    success_patterns: List[str] = field(
        default_factory=lambda: [
            'ieeexplore.ieee.org',
            'IEEE'
        ]
    )
    
    # Timeouts and limits
    timeout: int = field(
        default_factory=lambda: int(os.getenv('IEEE_TIMEOUT', '30'))
    )
    rate_limit: float = field(
        default_factory=lambda: float(os.getenv('IEEE_RATE_LIMIT', '2.0'))
    )
    max_retries: int = field(
        default_factory=lambda: int(os.getenv('IEEE_MAX_RETRIES', '3'))
    )
    
    # Circuit breaker
    circuit_breaker_threshold: int = field(
        default_factory=lambda: int(os.getenv('IEEE_CB_THRESHOLD', '5'))
    )
    circuit_breaker_timeout: int = field(
        default_factory=lambda: int(os.getenv('IEEE_CB_TIMEOUT', '300'))
    )
    
    # Session
    session_file: str = field(
        default_factory=lambda: os.getenv(
            'IEEE_SESSION_FILE',
            '.sessions/ieee_session.json'
        )
    )


@dataclass
class ScopusConfig:
    """Configuration for Scopus connector.
    
    This dataclass centralizes all configuration parameters for the Scopus
    connector, including URLs, timeouts, rate limits, and API settings.
    
    Values can be loaded from environment variables or provided directly.
    
    Attributes:
        api_base_url: Base URL for Elsevier API
        api_search_endpoint: Search endpoint path
        api_abstract_endpoint: Abstract retrieval endpoint path
        web_login_url: EZproxy login URL for Scopus
        web_home_url: Scopus home URL (via proxy)
        success_patterns: URL/title patterns indicating successful login
        timeout: Request timeout in seconds
        rate_limit: Delay between requests in seconds
        max_retries: Maximum retry attempts for failed requests
        session_file: Path to session cookie file
        max_parallel_abstracts: Maximum abstracts to fetch in parallel
    """
    
    # API endpoints
    api_base_url: str = field(
        default_factory=lambda: os.getenv(
            'SCOPUS_API_BASE_URL',
            'https://api.elsevier.com'
        )
    )
    api_search_endpoint: str = field(
        default_factory=lambda: os.getenv(
            'SCOPUS_API_SEARCH_ENDPOINT',
            '/content/search/scopus'
        )
    )
    api_abstract_endpoint: str = field(
        default_factory=lambda: os.getenv(
            'SCOPUS_API_ABSTRACT_ENDPOINT',
            '/content/abstract/scopus_id'
        )
    )
    
    # Web endpoints
    web_login_url: str = field(
        default_factory=lambda: os.getenv(
            'SCOPUS_WEB_LOGIN_URL',
            'https://bvirtual.epn.edu.ec/login?url=http://www.scopus.com'
        )
    )
    web_home_url: str = field(
        default_factory=lambda: os.getenv(
            'SCOPUS_WEB_HOME_URL',
            'https://bvirtual.epn.edu.ec:2057/pages/home?display=basic#basic'
        )
    )
    
    # Success indicators for authentication
    success_patterns: List[str] = field(
        default_factory=lambda: [
            'scopus.com',
            'Scopus'
        ]
    )
    
    # Timeouts and limits
    timeout: int = field(
        default_factory=lambda: int(os.getenv('SCOPUS_TIMEOUT', '30'))
    )
    rate_limit: float = field(
        default_factory=lambda: float(os.getenv('SCOPUS_RATE_LIMIT', '1.0'))
    )
    max_retries: int = field(
        default_factory=lambda: int(os.getenv('SCOPUS_MAX_RETRIES', '3'))
    )
    
    # Session
    session_file: str = field(
        default_factory=lambda: os.getenv(
            'SCOPUS_SESSION_FILE',
            '.sessions/scopus_session.json'
        )
    )
    
    # Parallel processing
    max_parallel_abstracts: int = field(
        default_factory=lambda: int(os.getenv('SCOPUS_MAX_PARALLEL_ABSTRACTS', '10'))
    )
