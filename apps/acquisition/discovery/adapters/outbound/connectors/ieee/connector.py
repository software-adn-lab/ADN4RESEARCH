from typing import Iterable, Dict, Any, Optional
import logging

from apps.acquisition.discovery.domain.interfaces.i_academic_connector import IAcademicConnector
from apps.acquisition.shared.infrastructure.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from apps.acquisition.discovery.infrastructure.http import HttpClient, RateLimiter
from apps.acquisition.discovery.infrastructure.normalization import IeeeResultNormalizer
from apps.acquisition.discovery.infrastructure.config import IeeeConfig
from .strategies import SearchStrategy, IeeeApiStrategy, IeeeWebStrategy

logger = logging.getLogger(__name__)


class IeeeConnector(IAcademicConnector):
    """
    Refactored IEEE Xplore connector using Strategy pattern.

    This connector orchestrates search execution by selecting the best
    available strategy (API or Web scraping). It no longer contains
    direct HTTP or Playwright code - all implementation details are
    delegated to strategies.

    Características:
    - Strategy selection based on availability
    - Circuit breaker for fault tolerance
    - Rate limiting to avoid blocking
    - Clean separation of concerns
    """

    def __init__(
        self,
        username: str,
        password: str,
        headless: bool = True,
        rate_limit: float = None,
        prefer_api: bool = True,
        config: Optional[IeeeConfig] = None,
        api_strategy: Optional[IeeeApiStrategy] = None,
        web_strategy: Optional[IeeeWebStrategy] = None,
        rate_limiter: Optional[RateLimiter] = None,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        """
        Args:
            username: Correo institucional EPN
            password: Contraseña institucional
            headless: Ejecutar navegador sin ventana (para web strategy)
            rate_limit: Segundos de espera entre búsquedas (uses config if None)
            prefer_api: Si True, intenta API primero; si False, usa web scraping
            config: Optional IeeeConfig (created with defaults if not provided)
            api_strategy: Optional API strategy (created if not provided)
            web_strategy: Optional web strategy (created if not provided)
            rate_limiter: Optional rate limiter (created if not provided)
            circuit_breaker: Optional circuit breaker (created if not provided)
        """
        self.username = username
        self.password = password
        self.prefer_api = prefer_api
        
        # Initialize or use provided config
        if config is None:
            config = IeeeConfig()
        self.config = config
        
        # Create normalizer (shared by strategies)
        normalizer = IeeeResultNormalizer()
        
        # Initialize or use provided strategies
        if api_strategy is None:
            http_client = HttpClient(timeout=config.timeout)
            api_strategy = IeeeApiStrategy(
                http_client=http_client,
                normalizer=normalizer,
                api_url=config.api_search_url,
                test_url=config.api_test_url
            )
        
        if web_strategy is None:
            web_strategy = IeeeWebStrategy(
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
        
        # Initialize circuit breaker
        if circuit_breaker is None:
            circuit_breaker = CircuitBreaker(
                fail_max=config.circuit_breaker_threshold,
                timeout_duration=config.circuit_breaker_timeout,
                name="IEEE Xplore"
            )
        self.circuit_breaker = circuit_breaker

    def search(self, query: str, max_results: int = 10) -> Iterable[Dict[str, Any]]:
        """
        Busca en IEEE Xplore usando la mejor estrategia disponible.

        Args:
            query: Término de búsqueda
            max_results: Máximo de resultados a retornar

        Returns:
            Iterable de diccionarios con:
            {
                'title': str,
                'link': str,
                'doi': str | None,
                'source': 'IEEE Xplore',
                'year': int | None,
                'authors': List[str],
                'abstract': str | None,
                'is_open_access': bool | None,
                'pdf_url': str | None
            }
        """
        try:
            # Execute search with circuit breaker protection
            results = self.circuit_breaker.call(
                self._search_with_strategy,
                query,
                max_results
            )
            
            # Yield results
            for result in results:
                yield result
            
            # Apply rate limiting
            self.rate_limiter.wait()

        except CircuitBreakerOpenError as e:
            logger.error(f"Circuit breaker open: {e}")
            return []

        except Exception as e:
            logger.error(f"Error en búsqueda IEEE: {e}")
            raise

    def _search_with_strategy(self, query: str, max_results: int) -> list:
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
            Exception: If no strategy can execute
        """
        logger.info(f"Buscando en IEEE: '{query}' (max: {max_results})")
        
        # Try API strategy first if preferred
        if self.prefer_api and self.api_strategy.can_execute():
            try:
                logger.info("Using API strategy")
                return self.api_strategy.execute(query, max_results)
            except Exception as e:
                logger.warning(f"API strategy failed: {e}, trying web strategy")
        
        # Fallback to web strategy
        if self.web_strategy.can_execute():
            logger.info("Using web scraping strategy")
            return self.web_strategy.execute(query, max_results)
        
        # No strategy available
        raise Exception(
            "No available search strategy. "
            "API is not accessible and credentials are missing for web scraping."
        )



    def find_metadata(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Busca metadatos de un estudio específico por título.

        Actualmente no implementado para IEEE Xplore.
        """
        logger.debug(f"find_metadata no implementado en IeeeConnector: {title}")
        return None

    def close(self):
        """
        Cierra recursos asociados al conector.
        
        Strategies manage their own resources, so this is mainly
        for interface compliance.
        """
        logger.info("IeeeConnector cerrado")
