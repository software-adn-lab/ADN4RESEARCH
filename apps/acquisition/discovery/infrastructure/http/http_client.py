"""HTTP client wrapper with automatic retry logic."""

import logging
from typing import Dict, Any, Optional
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

logger = logging.getLogger(__name__)


class HttpClient:
    """Wrapper around requests.Session with retry logic.
    
    This class provides a simplified interface for making HTTP requests
    with automatic retry on transient failures. It uses exponential backoff
    to avoid overwhelming failing services.
    
    Attributes:
        session: The underlying requests.Session object
        timeout: Default timeout for requests in seconds
        max_retries: Maximum number of retry attempts
    """
    
    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        default_headers: Optional[Dict[str, str]] = None
    ):
        """Initialize HttpClient with configuration.
        
        Args:
            timeout: Default timeout for requests in seconds
            max_retries: Maximum number of retry attempts (default: 3)
            default_headers: Optional dictionary of headers to include in all requests
        """
        self.session = requests.Session()
        self.timeout = timeout
        self.max_retries = max_retries
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*'
        })
        
        if default_headers:
            self.session.headers.update(default_headers)
        
        logger.debug(
            f"HttpClient initialized with timeout={timeout}s, "
            f"max_retries={max_retries}"
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError
        )),
        reraise=True
    )
    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        **kwargs
    ) -> requests.Response:
        """GET request with automatic retries.
        
        Retries on connection errors, timeouts, and HTTP errors (5xx).
        Uses exponential backoff: 2s, 4s, 8s (capped at 10s).
        
        Args:
            url: URL to request
            params: Optional query parameters
            headers: Optional headers (merged with default headers)
            timeout: Optional timeout override (uses default if not specified)
            **kwargs: Additional arguments passed to requests.get
            
        Returns:
            Response object
            
        Raises:
            requests.exceptions.RequestException: If all retries fail
        """
        timeout = timeout or self.timeout
        
        try:
            logger.debug(f"GET {url}")
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout,
                **kwargs
            )
            
            # Raise HTTPError for bad status codes (4xx, 5xx)
            # This will trigger retry for 5xx errors
            response.raise_for_status()
            
            logger.debug(f"GET {url} -> {response.status_code}")
            return response
            
        except requests.exceptions.HTTPError as e:
            # Only retry on 5xx server errors, not 4xx client errors
            if e.response is not None and 500 <= e.response.status_code < 600:
                logger.warning(f"Server error on GET {url}: {e}, will retry")
                raise
            else:
                logger.error(f"Client error on GET {url}: {e}, not retrying")
                raise
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.warning(f"Transient error on GET {url}: {e}, will retry")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError
        )),
        reraise=True
    )
    def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        **kwargs
    ) -> requests.Response:
        """POST request with automatic retries.
        
        Retries on connection errors, timeouts, and HTTP errors (5xx).
        Uses exponential backoff: 2s, 4s, 8s (capped at 10s).
        
        Args:
            url: URL to request
            data: Optional form data
            json: Optional JSON data
            headers: Optional headers (merged with default headers)
            timeout: Optional timeout override (uses default if not specified)
            **kwargs: Additional arguments passed to requests.post
            
        Returns:
            Response object
            
        Raises:
            requests.exceptions.RequestException: If all retries fail
        """
        timeout = timeout or self.timeout
        
        try:
            logger.debug(f"POST {url}")
            response = self.session.post(
                url,
                data=data,
                json=json,
                headers=headers,
                timeout=timeout,
                **kwargs
            )
            
            # Raise HTTPError for bad status codes (4xx, 5xx)
            response.raise_for_status()
            
            logger.debug(f"POST {url} -> {response.status_code}")
            return response
            
        except requests.exceptions.HTTPError as e:
            # Only retry on 5xx server errors, not 4xx client errors
            if e.response is not None and 500 <= e.response.status_code < 600:
                logger.warning(f"Server error on POST {url}: {e}, will retry")
                raise
            else:
                logger.error(f"Client error on POST {url}: {e}, not retrying")
                raise
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.warning(f"Transient error on POST {url}: {e}, will retry")
            raise
    
    def set_cookies(self, cookies: Dict[str, str]) -> None:
        """Set cookies on the session.
        
        Args:
            cookies: Dictionary of cookie name-value pairs
        """
        for name, value in cookies.items():
            self.session.cookies.set(name, value)
        
        logger.debug(f"Set {len(cookies)} cookies on session")
    
    def get_cookies(self) -> Dict[str, str]:
        """Get current session cookies.
        
        Returns:
            Dictionary of cookie name-value pairs
        """
        return dict(self.session.cookies)
    
    def close(self) -> None:
        """Close the underlying session and release resources."""
        self.session.close()
        logger.debug("HttpClient session closed")
