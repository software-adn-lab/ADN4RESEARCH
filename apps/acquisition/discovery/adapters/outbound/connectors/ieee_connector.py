"""
IEEE Xplore Connector con sesión persistente y detección automática de red.

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

CARACTERÍSTICAS:
- NO abre navegador en búsquedas subsecuentes (rápido y eficiente)
- Usa endpoint /rest/search para obtener JSON directo (no scraping HTML)
- Rate limiting con variación aleatoria (anti-detección)
- Retry automático con backoff exponencial
- Paginación automática
"""
from typing import Iterable, Dict, Any
import logging
import time
import random
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

from apps.acquisition.discovery.domain.interfaces.i_academic_connector import IAcademicConnector
from .ieee_session_manager import IeeeSessionManager

logger = logging.getLogger(__name__)


class IeeeConnector(IAcademicConnector):
    """
    Conector para IEEE Xplore vía EZproxy con sesión persistente.

    Características:
    - Autenticación automática vía Playwright (solo primera vez)
    - Reutiliza cookies guardadas (sin browser para búsquedas)
    - Re-autentica automáticamente si sesión expira
    - Usa endpoint /rest/search para obtener JSON directo
    """

    # URLs - Búsqueda DIRECTA a IEEE (EZproxy se usa SOLO para autenticación)
    # Una vez autenticado con cookies, las búsquedas van directo a ieeexplore.ieee.org
    IEEE_SEARCH_API = "https://ieeexplore.ieee.org/rest/search"
    IEEE_HOME = "https://ieeexplore.ieee.org/Xplore/home.jsp"

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
        self.session_manager = IeeeSessionManager(
            username=username,
            password=password,
            headless=headless
        )

    def search(self, query: str, max_results: int = 10) -> Iterable[Dict[str, Any]]:
        """
        Busca en IEEE Xplore usando sesión persistente.

        Args:
            query: Término de búsqueda
            max_results: Máximo de resultados a retornar

        Yields:
            Diccionarios con estructura:
            {
                'title': str,
                'link': str,
                'doi': str | None,
                'source': 'IEEE Xplore'
            }
        """
        try:
            # Asegurar autenticación (usa cookies si existen, autentica si no)
            if not self.session_manager.ensure_authenticated():
                raise Exception("No se pudo autenticar en IEEE Xplore")

            logger.info(f"Buscando en IEEE: '{query}' (max: {max_results})")

            # Búsqueda vía /rest/search con requests (SIN browser)
            try:
                api_results_iter = self._search_via_api(query, max_results)
                results = list(api_results_iter)
            except ValueError as api_error:
                logger.warning(f"Fallo en API JSON de IEEE, usando fallback Playwright: {api_error}")
                # Fallback más robusto usando Playwright dentro del contexto del navegador real
                from .ieee_playwright_connector import IeeePlaywrightConnector

                with IeeePlaywrightConnector(
                    username=self.username,
                    password=self.password,
                    headless=self.headless,
                    rate_limit=self.rate_limit
                ) as fallback_connector:
                    results = list(fallback_connector.search(query, max_results=max_results))

            # Rate limiting con variación random (parecer más humano)
            # Evita patrones perfectamente rítmicos que activan detección
            delay = self.rate_limit + random.uniform(0.5, 1.5)
            logger.debug(f"Rate limit: esperando {delay:.2f}s")
            time.sleep(delay)

            return results

        except Exception as e:
            logger.error(f"Error en búsqueda IEEE: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.RequestException, ConnectionError)),
        reraise=True
    )
    def _search_via_api(self, query: str, max_results: int) -> Iterable[Dict[str, Any]]:
        """
        Ejecuta búsqueda usando /rest/search endpoint.

        Usa las cookies guardadas en session_manager.session (NO abre browser).

        Retries automáticos:
        - Máximo 3 intentos
        - Backoff exponencial: 2s, 4s, 8s (con jitter)
        - Solo reintenta errores de red/conexión
        """
        try:
            # Calcular paginación
            page_size = min(max_results, 100)  # IEEE acepta hasta 100 por página
            total_fetched = 0
            page_number = 1

            while total_fetched < max_results:
                # Request al endpoint de búsqueda
                payload = {
                    "queryText": query,
                    "highlight": True,
                    "returnFacets": ["ALL"],
                    "returnType": "SEARCH",
                    "matchPubs": True,
                    "pageNumber": page_number,
                    "rowsPerPage": page_size
                }

                logger.debug(f"POST {self.IEEE_SEARCH_API} (página {page_number})")

                response = self.session_manager.session.post(
                    self.IEEE_SEARCH_API,
                    json=payload,
                    timeout=30
                )

                # Verificar si sesión expiró
                if response.status_code == 302 or response.status_code == 401:
                    logger.warning("Sesión expirada, re-autenticando...")
                    self.session_manager._authenticate()

                    # Reintentar request
                    response = self.session_manager.session.post(
                        self.IEEE_SEARCH_API,
                        json=payload,
                        timeout=30
                    )

                content_type = response.headers.get("Content-Type", "")
                is_json_response = response.status_code == 200 and "application/json" in content_type.lower()
                if not is_json_response:
                    logger.error(f"IEEE: Respuesta inesperada. Status: {response.status_code}")
                    logger.error(f"Contenido (HTML?): {response.text[:1000]}...")
                    try:
                        with open("debug_ieee_error.html", "w", encoding="utf-8") as f:
                            f.write(response.text)
                        logger.info("Respuesta de error de IEEE guardada en debug_ieee_error.html")
                    except Exception as file_error:
                        logger.error(f"No se pudo guardar el archivo de debug: {file_error}")
                    if response.status_code != 200:
                        response.raise_for_status()
                    raise ValueError("IEEE: La respuesta no es JSON, revisar debug_ieee_error.html")

                response.raise_for_status()
                data = response.json()

                # Extraer resultados
                records = data.get('records', [])
                total_records = data.get('totalRecords', 0)

                logger.info(f"✓ Página {page_number}: {len(records)} resultados (total disponible: {total_records})")

                if not records:
                    break

                # Yield resultados normalizados
                for record in records:
                    if total_fetched >= max_results:
                        break

                    yield self._normalize_record(record)
                    total_fetched += 1

                # Si no hay más páginas, salir
                if total_fetched >= total_records or len(records) < page_size:
                    break

                page_number += 1

            logger.info(f"✓ Total retornado: {total_fetched} resultados")

        except Exception as e:
            logger.error(f"Error en API search: {e}")
            raise

    def _normalize_record(self, record: Dict) -> Dict[str, Any]:
        """
        Normaliza un registro de /rest/search al contrato esperado.

        Campos disponibles en record:
        - articleNumber
        - articleTitle
        - doi
        - publicationYear
        - authors
        - abstract
        - etc.
        """
        article_number = record.get('articleNumber', '')

        return {
            'title': record.get('articleTitle', 'N/A'),
            'link': f"https://ieeexplore.ieee.org/document/{article_number}" if article_number else '',
            'doi': record.get('doi'),
            'source': 'IEEE Xplore',
            # Campos adicionales opcionales
            'year': record.get('publicationYear'),
            'authors': self._extract_authors(record.get('authors', [])),
            'abstract': record.get('abstract', '').strip() if record.get('abstract') else None
        }

    def _extract_authors(self, authors_data: list) -> list:
        """Extrae nombres de autores del formato IEEE"""
        if not authors_data:
            return []

        author_names = []
        for author in authors_data:
            if isinstance(author, dict):
                # IEEE usa 'preferredName' como campo principal
                # También puede tener 'fullName', 'name', o 'normalizedName'
                name = (
                    author.get('preferredName') or
                    author.get('fullName') or
                    author.get('name') or
                    author.get('normalizedName', '')
                )
                if name:
                    author_names.append(name)
            elif isinstance(author, str):
                author_names.append(author)

        return author_names

    def close(self):
        """
        Cierra recursos (si hubiera).

        Nota: Las cookies se mantienen guardadas en disco para futuras ejecuciones.
        """
        logger.info("IeeeConnector cerrado (sesión guardada en disco)")
