import logging
from typing import Dict, List, Any, Iterable, Optional

from apps.acquisition.discovery.domain.interfaces.i_academic_connector import IAcademicConnector
from apps.acquisition.discovery.infrastructure.http import HttpClient, RateLimiter
from apps.acquisition.discovery.infrastructure.normalization import ScopusResultNormalizer
from apps.acquisition.discovery.infrastructure.config import ScopusConfig
from .strategies import SearchStrategy, ScopusApiStrategy, ScopusWebStrategy

logger = logging.getLogger(__name__)


class ScopusConnector(IAcademicConnector):
    """
    Refactored Scopus connector using Strategy pattern.

    This connector orchestrates search execution by selecting the best
    available strategy (API or Web scraping). It no longer contains
    direct HTTP or Playwright code - all implementation details are
    delegated to strategies.

    Características:
    - Strategy selection based on availability
    - Rate limiting to avoid blocking
    - Clean separation of concerns
    - Backward compatible interface
    """

    def __init__(
        self,
        username: str = None,
        password: str = None,
        api_key: str = None,
        headless: bool = True,
        rate_limit: float = None,
        prefer_api: bool = True,
        config: Optional[ScopusConfig] = None,
        api_strategy: Optional[ScopusApiStrategy] = None,
        web_strategy: Optional[ScopusWebStrategy] = None,
        rate_limiter: Optional[RateLimiter] = None
    ):
        """
        Args:
            username: Correo institucional (para web strategy)
            password: Contraseña institucional (para web strategy)
            api_key: Elsevier API key (para API strategy)
            headless: Ejecutar navegador sin ventana (para web strategy)
            rate_limit: Segundos de espera entre búsquedas (uses config if None)
            prefer_api: Si True, intenta API primero; si False, usa web scraping
            config: Optional ScopusConfig (created with defaults if not provided)
            api_strategy: Optional API strategy (created if not provided)
            web_strategy: Optional web strategy (created if not provided)
            rate_limiter: Optional rate limiter (created if not provided)
        """
        self.username = username
        self.password = password
        self.api_key = api_key
        self.prefer_api = prefer_api
        
        # Initialize or use provided config
        if config is None:
            config = ScopusConfig()
        self.config = config
        
        # Create normalizer (shared by strategies)
        normalizer = ScopusResultNormalizer()
        
        # Initialize or use provided strategies
        if api_strategy is None and api_key:
            http_client = HttpClient(timeout=config.timeout)
            api_strategy = ScopusApiStrategy(
                http_client=http_client,
                normalizer=normalizer,
                api_key=api_key,
                base_url=config.api_base_url
            )
        
        if web_strategy is None and username and password:
            web_strategy = ScopusWebStrategy(
                username=username,
                password=password,
                normalizer=normalizer,
                headless=headless
            )
        
        self.api_strategy = api_strategy
        self.web_strategy = web_strategy
        
        # Initialize rate limiter
        if rate_limiter is None:
            effective_rate = rate_limit if rate_limit is not None else config.rate_limit
            rate_limiter = RateLimiter(rate=effective_rate)
        self.rate_limiter = rate_limiter

    def search(
        self,
        query: str,
        max_results: int = 25
    ) -> Iterable[Dict[str, Any]]:
        """
        Busca en Scopus usando la mejor estrategia disponible.

        Args:
            query: Término de búsqueda
            max_results: Máximo de resultados a retornar

        Yields:
            Diccionarios con estructura normalizada
        """
        try:
            # Execute search with strategy selection
            results = self._search_with_strategy(query, max_results)
            
            # Yield results
            for result in results:
                yield result
            
            # Apply rate limiting
            self.rate_limiter.wait()

        except Exception as e:
            logger.error(f"Error en búsqueda Scopus: {e}")
            raise
    
    def _search_with_strategy(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Select and execute the best available search strategy.
        
        Strategy selection logic:
        1. If prefer_api is True and API is available, use API strategy
        2. If API fails or is not preferred, try web strategy
        3. If no strategy is available, raise exception
        
        Args:
            query: Search query
            max_results: Maximum results to return
            
        Returns:
            List of normalized results
            
        Raises:
            ValueError: If no strategy can execute
        """
        logger.info(f"Buscando en Scopus: '{query}' (max: {max_results})")
        
        # Try API strategy first if preferred and available
        if self.prefer_api and self.api_strategy and self.api_strategy.can_execute():
            try:
                logger.info("Using Scopus API strategy")
                return self.api_strategy.execute(query, max_results)
            except Exception as e:
                logger.warning(f"API strategy failed: {e}, trying web strategy")
        
        # Fallback to web strategy
        if self.web_strategy and self.web_strategy.can_execute():
            logger.info("Using Scopus web scraping strategy")
            return self.web_strategy.execute(query, max_results)
        
        # No strategy available
        raise ValueError(
            "No available search strategy for Scopus. "
            "API is not accessible and credentials are missing for web scraping."
        )



    def find_metadata(
        self,
        title: str,
        authors: Optional[List[str]] = None,
        year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Busca metadatos de un artículo por título.
        
        Uses API strategy if available to search for specific title.
        Implements IAcademicConnector interface with additional optional parameters.
        
        Args:
            title: Article title to search for (required by interface)
            authors: Optional list of authors for matching (Scopus-specific)
            year: Optional publication year for matching (Scopus-specific)
            
        Returns:
            Normalized metadata dictionary or None if not found
        """
        if not title or not title.strip():
            return None
        
        if not self.api_strategy or not self.api_strategy.can_execute():
            logger.debug("Cannot find metadata: API strategy not available")
            return None
        
        try:
            # Search with exact title
            query = f'TITLE("{title.strip()}")'
            results = self.api_strategy.execute(query, max_results=5)
            
            if results:
                # Return first result (best match)
                return results[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding metadata for '{title}': {e}")
            return None
