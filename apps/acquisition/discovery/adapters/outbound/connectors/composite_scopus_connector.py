"""
Composite Scopus Connector - Híbrido con fallback automático.

Estrategia de resiliencia para Scopus:
1. Intento primario: API oficial de Elsevier (rápido, limpio, cuota limitada)
2. Fallback automático: Playwright + APIs internas (lento pero robusto)
3. Circuit Breaker: Evita saturar servicios caídos

Este conector NUNCA falla. Si ambas vías fallan, devuelve lista vacía
pero registra el error para que el flujo continúe.

Uso:
    connector = CompositeScopusConnector(
        api_key="xxx",
        username="usuario@epn.edu.ec",
        password="pass",
        headless=True
    )

    results = connector.search("machine learning", max_results=10)
    # Intenta API → Si falla → Intenta Playwright → Si falla → []
"""
import logging
from typing import Dict, List, Any, Generator, Optional

from apps.acquisition.discovery.domain.interfaces.i_academic_connector import IAcademicConnector
from apps.acquisition.shared.infrastructure.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from .scopus_connector import ScopusConnector
from .scopus_playwright_connector import ScopusPlaywrightConnector

logger = logging.getLogger(__name__)


class CompositeScopusConnector(IAcademicConnector):
    """
    Conector híbrido para Scopus con tolerancia a fallos.

    Combina:
    - API oficial (prioridad alta, rápida)
    - Scraping Playwright (fallback robusto)
    - Circuit Breaker (protección contra servicios caídos)

    El flujo NUNCA explota. Si todo falla, devuelve [] y loguea el error.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        headless: bool | None = None,
        rate_limit: float = 1.0,
        preloaded_cookies: Optional[str] = None
    ):
        """
        Args:
            api_key: API key de Elsevier (para API oficial)
            username: Usuario EPN (para fallback Playwright)
            password: Contraseña EPN (para fallback Playwright)
            headless: Navegador sin interfaz. Si es None, usa HEADLESS_MODE del .env.
            rate_limit: Segundos entre peticiones
            preloaded_cookies: Cookies JSON exportadas (opcional, para bypass reCAPTCHA)
        """
        # Usar configuración centralizada si no se especifica explícitamente
        from apps.acquisition.shared.config.playwright_config import get_playwright_config
        cfg = get_playwright_config()

        self.api_key = api_key
        self.username = username
        self.password = password
        self.headless = cfg.headless if headless is None else headless
        self.rate_limit = rate_limit
        self.preloaded_cookies = preloaded_cookies

        # Conectores individuales
        self.api_connector = None
        self.playwright_connector = None

        # Inicializar API connector si hay clave
        if api_key:
            self.api_connector = ScopusConnector(
                api_key=api_key,
                username=username,
                password=password,
                headless=headless,
                rate_limit=rate_limit
            )
            logger.info("✅ Scopus API habilitada")
        else:
            logger.warning("⚠️ Sin API key de Scopus. Solo fallback Playwright disponible.")

        # Inicializar Playwright connector si hay credenciales O cookies preloaded
        if (username and password) or preloaded_cookies:
            self.playwright_connector = ScopusPlaywrightConnector(
                username=username or "",
                password=password or "",
                headless=headless,
                preloaded_cookies=preloaded_cookies
            )
            if preloaded_cookies:
                logger.info("✅ Scopus Playwright (fallback) habilitado con cookies preloaded (bypass reCAPTCHA)")
            else:
                logger.info("✅ Scopus Playwright (fallback) habilitado")
        else:
            logger.warning("⚠️ Sin credenciales EPN ni cookies preloaded. Fallback Playwright no disponible.")

        # Circuit Breaker para la API (proteger cuota)
        self.api_circuit_breaker = CircuitBreaker(
            fail_max=3,  # Menos intentos que IEEE (la API es más estable)
            timeout_duration=600,  # 10 minutos
            name="Scopus API"
        )

    def search(
        self,
        query: str,
        max_results: int = 25
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Busca en Scopus con fallback automático.

        Orden de intentos:
        1. API oficial (si está disponible y el circuit breaker cerrado)
        2. Playwright (si API falla o está bloqueada)
        3. Lista vacía (si ambos fallan, pero NO explota el flujo)

        Args:
            query: Término de búsqueda
            max_results: Máximo de resultados

        Yields:
            Dict normalizado con title, link, doi, source, is_open_access, pdf_url
        """
        results = []

        # ================================================================
        # INTENTO 1: API oficial de Elsevier
        # ================================================================
        if self.api_connector:
            try:
                logger.info("[Composite Scopus] Intentando vía API oficial...")
                results = self.api_circuit_breaker.call(
                    self._search_via_api,
                    query,
                    max_results
                )

                if results:
                    logger.info(f"✅ [API] Obtenidos {len(results)} resultados de Scopus API")
                    for result in results:
                        yield result
                    return  # Éxito, salir

                else:
                    # API respondió pero sin resultados
                    logger.warning("⚠️ [API] Sin resultados en Scopus API. Probando fallback...")

            except CircuitBreakerOpenError as e:
                # Circuit Breaker abierto (API caída o cuota agotada)
                logger.warning(f"⚠️ [API] {e}. Usando fallback Playwright...")

            except Exception as e:
                # Otro error (red, parsing, etc.)
                logger.warning(f"⚠️ [API] Error en Scopus API: {type(e).__name__}. Usando fallback Playwright...")

        # ================================================================
        # INTENTO 2: Playwright (scraping como fallback)
        # ================================================================
        if self.playwright_connector:
            try:
                logger.info("[Composite Scopus] Activando fallback Playwright...")
                results = list(self.playwright_connector.search(query, max_results))

                if results:
                    logger.info(f"✅ [Playwright] Obtenidos {len(results)} resultados de Scopus Playwright")
                    for result in results:
                        yield result
                    return  # Éxito, salir

                else:
                    logger.warning("⚠️ [Playwright] Sin resultados en Scopus Playwright.")

            except Exception as e:
                logger.error(f"❌ [Playwright] Error en fallback: {type(e).__name__}: {e}")

        # ================================================================
        # FALLO TOTAL: Ambas vías fallaron
        # ================================================================
        logger.error(
            "❌ [Composite Scopus] Todas las vías de Scopus fallaron. "
            "Retornando lista vacía para no romper el flujo."
        )
        return iter([])  # Generador vacío

    def _search_via_api(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Wrapper para búsqueda API protegida por Circuit Breaker.

        Esta función se ejecuta solo si el Circuit Breaker está cerrado.
        """
        return list(self.api_connector.search(query, max_results))

    def find_metadata(
        self,
        title: str,
        authors: Optional[List[str]] = None,
        year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Busca metadatos de un estudio específico.

        Intenta API primero, luego fallback (no implementado en Playwright aún).

        Args:
            title: Título del estudio
            authors: Lista de autores (opcional)
            year: Año de publicación (opcional)

        Returns:
            Dict con metadatos o None
        """
        if self.api_connector:
            try:
                return self.api_connector.find_metadata(title, authors, year)
            except Exception as e:
                logger.warning(f"⚠️ Error en find_metadata (API): {e}")

        # TODO: Implementar find_metadata en PlaywrightConnector
        logger.warning("⚠️ find_metadata no disponible en fallback Playwright")
        return None

    def close(self):
        """Cierra recursos de ambos conectores."""
        if self.api_connector:
            self.api_connector.close()

        if self.playwright_connector:
            self.playwright_connector.close()

        logger.info("CompositeScopusConnector cerrado")
