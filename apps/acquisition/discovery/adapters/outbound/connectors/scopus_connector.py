"""
Scopus Connector con sesión persistente y detección automática de red.

DETECCIÓN AUTOMÁTICA DE RED:
- EN LA RED universitaria (EPN): Acceso directo por IP → sin login → sin cookies → RÁPIDO
- FUERA de la red: Autenticación automática con Playwright → guarda cookies → usa cookies

FLUJO:
1. Primera búsqueda:
   a. Intenta acceso directo por IP (red universitaria)
   b. Si falla: Autentica con Playwright → guarda cookies → busca con requests
2. Siguientes búsquedas:
   a. Si estás en la red: Acceso directo (sin cookies)
   b. Si estás fuera: Usa cookies guardadas
3. Si cookies expiran: Re-autentica automáticamente

ESTADO ACTUAL:
⚠️  TODO: Identificar endpoint de búsqueda de Scopus mediante captura XHR
    Endpoints posibles:
    - /api/search
    - /results/results.uri
    - Algún endpoint REST interno

    Proceso para descubrir endpoint:
    1. Ejecutar navegador con Playwright
    2. Hacer búsqueda de prueba en Scopus
    3. Capturar peticiones XHR/Fetch
    4. Identificar endpoint que retorna resultados en JSON
"""
from typing import Iterable, Dict, Any
import logging
import time
import random
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

from apps.acquisition.discovery.domain.interfaces.i_academic_connector import IAcademicConnector
from .scopus_session_manager import ScopusSessionManager

logger = logging.getLogger(__name__)


class ScopusConnector(IAcademicConnector):
    """
    Conector para Scopus vía EZproxy con sesión persistente.

    Características:
    - Autenticación automática vía Playwright (solo primera vez)
    - Reutiliza cookies guardadas (sin browser para búsquedas)
    - Re-autentica automáticamente si sesión expira

    TODO: Identificar endpoint exacto de búsqueda de Scopus
    """

    # URLs (pueden necesitar ajuste según la estructura real de Scopus)
    SCOPUS_SEARCH_URL = "https://www.scopus.com/results/results.uri"
    SCOPUS_API_SEARCH = "https://www.scopus.com/api/search"  # Posible endpoint
    SCOPUS_HOME = "https://www.scopus.com"

    def __init__(
        self,
        username: str,
        password: str,
        headless: bool = True,
        rate_limit: float = 2.0
    ):
        """
        Args:
            username: Correo institucional EPN
            password: Contraseña institucional
            headless: Ejecutar navegador sin ventana (solo para autenticación)
            rate_limit: Segundos de espera entre búsquedas
        """
        self.username = username
        self.password = password
        self.headless = headless
        self.rate_limit = rate_limit

        # Session manager (maneja autenticación y cookies)
        self.session_manager = ScopusSessionManager(
            username=username,
            password=password,
            headless=headless
        )

    def search(self, query: str, max_results: int = 10) -> Iterable[Dict[str, Any]]:
        """
        Busca en Scopus usando sesión persistente.

        Args:
            query: Término de búsqueda
            max_results: Máximo de resultados a retornar

        Yields:
            Diccionarios con estructura:
            {
                'title': str,
                'link': str,
                'doi': str | None,
                'source': 'Scopus'
            }

        TODO: Implementar lógica específica de búsqueda según endpoint real
        """
        try:
            # Asegurar autenticación (usa cookies si existen, autentica si no)
            if not self.session_manager.ensure_authenticated():
                raise Exception("No se pudo autenticar en Scopus")

            logger.info(f"Buscando en Scopus: '{query}' (max: {max_results})")

            # Búsqueda vía API/endpoint con requests (SIN browser)
            # NOTA: Esto requiere investigar el endpoint exacto de Scopus
            results = self._search_via_api(query, max_results)

            # Rate limiting con variación random (parecer más humano)
            delay = self.rate_limit + random.uniform(0.5, 1.5)
            logger.debug(f"Rate limit: esperando {delay:.2f}s")
            time.sleep(delay)

            return results

        except Exception as e:
            logger.error(f"Error en búsqueda Scopus: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.RequestException, ConnectionError)),
        reraise=True
    )
    def _search_via_api(self, query: str, max_results: int) -> Iterable[Dict[str, Any]]:
        """
        Ejecuta búsqueda usando endpoint de Scopus.

        Retries automáticos:
        - Máximo 3 intentos
        - Backoff exponencial: 2s, 4s, 8s
        - Solo reintenta errores de red/conexión

        TODO: Este método necesita ser implementado según el endpoint real.

        Opciones:
        1. Si Scopus tiene API REST interna: usar POST/GET con JSON
        2. Si no: usar Playwright para capturar XHR (similar a IEEE)
        3. Fallback: scraping HTML

        Por ahora, retorna ejemplo para demostración.
        """
        logger.warning("⚠️  _search_via_api no implementado completamente")
        logger.warning("   Se requiere investigar endpoint de búsqueda de Scopus")
        logger.warning("   Retornando resultados de ejemplo...")

        # TODO: Implementar búsqueda real
        # Ejemplo de cómo podría verse:
        """
        payload = {
            "query": query,
            "count": max_results,
            # Otros parámetros según Scopus
        }

        response = self.session_manager.session.post(
            self.SCOPUS_API_SEARCH,
            json=payload,
            timeout=30
        )

        # Manejar expiración de sesión
        if response.status_code == 302 or response.status_code == 401:
            logger.warning("Sesión expirada, re-autenticando...")
            self.session_manager._authenticate()
            response = self.session_manager.session.post(...)

        data = response.json()
        for record in data.get('results', []):
            yield self._normalize_record(record)
        """

        # Placeholder: retornar lista vacía por ahora
        logger.info("✓ Búsqueda Scopus: implementación pendiente")
        return []

    def _normalize_record(self, record: Dict) -> Dict[str, Any]:
        """
        Normaliza un registro de Scopus al contrato esperado.

        TODO: Ajustar según estructura real de respuesta de Scopus.
        """
        return {
            'title': record.get('title', 'N/A'),
            'link': record.get('link', ''),
            'doi': record.get('doi'),
            'source': 'Scopus',
            'year': record.get('year'),
            'authors': record.get('authors', []),
            'abstract': record.get('abstract')
        }

    def close(self):
        """
        Cierra recursos (si hubiera).

        Nota: Las cookies se mantienen guardadas en disco para futuras ejecuciones.
        """
        logger.info("ScopusConnector cerrado (sesión guardada en disco)")
