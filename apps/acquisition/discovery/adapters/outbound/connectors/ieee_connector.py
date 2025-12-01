from typing import Iterable, Dict, Any, Optional
import logging
import time
import random
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

from apps.acquisition.discovery.domain.interfaces.i_academic_connector import IAcademicConnector
from .ieee_session_manager import IeeeSessionManager
from apps.acquisition.shared.infrastructure.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

logger = logging.getLogger(__name__)


class IeeeConnector(IAcademicConnector):
    """
    Conector para IEEE Xplore con sesión persistente.

    Características:
    - Autenticación automática vía Playwright (solo primera vez si es necesario)
    - Reutiliza cookies guardadas (sin navegador para búsquedas normales)
    - Re-autentica si la sesión expira
    - Usa el endpoint /rest/search para obtener JSON
    """

    IEEE_PROXY_SEARCH = "https://bvirtual.epn.edu.ec:2097/rest/search"
    IEEE_DIRECT_SEARCH = "https://ieeexplore.ieee.org/rest/search"
    IEEE_HOME = "https://ieeexplore.ieee.org/Xplore/home.jsp"

    def __init__(
        self,
        username: str,
        password: str,
        headless: bool = True,
        rate_limit: float = 2.0,
        prefer_playwright: bool = True
    ):
        """
        Args:
            username: Correo institucional EPN
            password: Contraseña institucional
            headless: Ejecutar navegador sin ventana (solo para autenticación)
            rate_limit: Segundos de espera entre búsquedas
            prefer_playwright: Si True, usa Playwright directamente (más confiable);
                               si False, intenta API REST primero
        """
        self.username = username
        self.password = password
        self.headless = headless
        self.rate_limit = rate_limit
        self.prefer_playwright = prefer_playwright

        self.session_manager = IeeeSessionManager(
            username=username,
            password=password,
            headless=headless
        )

        self.circuit_breaker = CircuitBreaker(
            fail_max=5,
            timeout_duration=300,
            name="IEEE Xplore"
        )

    def search(self, query: str, max_results: int = 10) -> Iterable[Dict[str, Any]]:
        """
        Busca en IEEE Xplore usando sesión persistente y Circuit Breaker.

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
                'is_open_access': bool | None,
                'pdf_url': str | None
            }
        """
        try:
            results = self.circuit_breaker.call(self._search_protected, query, max_results)
            return results

        except CircuitBreakerOpenError as e:
            logger.error(str(e))
            return []

        except Exception as e:
            logger.error(f"Error en búsqueda IEEE: {e}")
            raise

    def _search_protected(self, query: str, max_results: int) -> list:
        """
        Lógica de búsqueda protegida por Circuit Breaker.
        """
        logger.info(f"Buscando en IEEE: '{query}' (max: {max_results})")

        if self.prefer_playwright:
            logger.info("Usando Playwright directamente (prefer_playwright=True)")
            from .ieee_playwright_connector import IeeePlaywrightConnector

            with IeeePlaywrightConnector(
                username=self.username,
                password=self.password,
                headless=self.headless,
                rate_limit=self.rate_limit
            ) as connector:
                results = list(connector.search(query, max_results=max_results))
        else:
            if not self.session_manager.ensure_authenticated():
                raise Exception("No se pudo autenticar en IEEE Xplore")

            try:
                api_results_iter = self._search_via_api(query, max_results)
                results = list(api_results_iter)
            except ValueError as api_error:
                logger.warning(f"Fallo en API JSON de IEEE, usando fallback Playwright: {api_error}")
                from .ieee_playwright_connector import IeeePlaywrightConnector

                with IeeePlaywrightConnector(
                    username=self.username,
                    password=self.password,
                    headless=self.headless,
                    rate_limit=self.rate_limit
                ) as fallback_connector:
                    results = list(fallback_connector.search(query, max_results=max_results))

        delay = self.rate_limit + random.uniform(0.5, 1.5)
        logger.debug(f"Rate limit: esperando {delay:.2f}s")
        time.sleep(delay)

        return results

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.RequestException, ConnectionError)),
        reraise=True
    )
    def _search_via_api(self, query: str, max_results: int) -> Iterable[Dict[str, Any]]:
        """
        Ejecuta búsqueda usando el endpoint /rest/search.

        Usa las cookies guardadas en session_manager.session.

        Retries automáticos:
        - Máximo 3 intentos
        - Backoff exponencial: 2s, 4s, 8s
        - Solo reintenta errores de red/conexión
        """
        try:
            page_size = min(max_results, 100)
            total_fetched = 0
            page_number = 1

            while total_fetched < max_results:
                payload = {
                    "queryText": query,
                    "highlight": True,
                    "returnFacets": ["ALL"],
                    "returnType": "SEARCH",
                    "matchPubs": True,
                    "pageNumber": page_number,
                    "rowsPerPage": page_size
                }

                search_url = self.IEEE_PROXY_SEARCH
                logger.debug(f"POST {search_url} (página {page_number})")

                response = self.session_manager.session.post(
                    search_url,
                    json=payload,
                    timeout=30,
                    allow_redirects=False
                )

                if response.status_code in (301, 302, 303, 307, 308, 401):
                    logger.warning(f"Sesión no válida ({response.status_code}), reautenticando...")
                    self.session_manager._authenticate()

                    response = self.session_manager.session.post(
                        search_url,
                        json=payload,
                        timeout=30,
                        allow_redirects=False
                    )

                content_type = response.headers.get("Content-Type", "")
                is_json_response = response.status_code == 200 and "application/json" in content_type.lower()
                if not is_json_response:
                    logger.error(f"IEEE: respuesta inesperada. Status: {response.status_code}")
                    logger.error(f"Contenido (posible HTML): {response.text[:1000]}...")
                    try:
                        with open("debug_ieee_error.html", "w", encoding="utf-8") as f:
                            f.write(response.text)
                        logger.info("Respuesta de error de IEEE guardada en debug_ieee_error.html")
                    except Exception as file_error:
                        logger.error(f"No se pudo guardar el archivo de debug: {file_error}")
                    if response.status_code != 200:
                        response.raise_for_status()
                    raise ValueError("IEEE: la respuesta no es JSON, revisar debug_ieee_error.html")

                response.raise_for_status()
                data = response.json()

                records = data.get('records', [])
                total_records = data.get('totalRecords', 0)

                logger.info(f"Página {page_number}: {len(records)} resultados (total disponible: {total_records})")

                if not records:
                    break

                for record in records:
                    if total_fetched >= max_results:
                        break

                    yield self._normalize_record(record)
                    total_fetched += 1

                if total_fetched >= total_records or len(records) < page_size:
                    break

                page_number += 1

            logger.info(f"Total retornado: {total_fetched} resultados")

        except Exception as e:
            logger.error(f"Error en API search: {e}")
            raise

    def _normalize_record(self, record: Dict) -> Dict[str, Any]:
        """
        Normaliza un registro del endpoint /rest/search al contrato esperado.
        """
        article_number = record.get('articleNumber', '')

        is_open_access, pdf_url = self._extract_access_info(record, article_number)

        return {
            'title': record.get('articleTitle', 'N/A'),
            'link': f"https://ieeexplore.ieee.org/document/{article_number}" if article_number else '',
            'doi': record.get('doi'),
            'source': 'IEEE Xplore',
            'year': record.get('publicationYear'),
            'authors': self._extract_authors(record.get('authors', [])),
            'abstract': record.get('abstract', '').strip() if record.get('abstract') else None,
            'is_open_access': is_open_access,
            'pdf_url': pdf_url,
        }

    def _extract_authors(self, authors_data: list) -> list:
        """
        Extrae nombres de autores desde la estructura de autores de IEEE.
        """
        if not authors_data:
            return []

        author_names = []
        for author in authors_data:
            if isinstance(author, dict):
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

    def _extract_access_info(
        self,
        record: Dict[str, Any],
        article_number: str
    ) -> tuple[Optional[bool], Optional[str]]:
        """
        Infere el estado de acceso abierto y posible URL del PDF desde el registro JSON.
        """
        is_open_access: Optional[bool] = None
        flag_fields = ["openAccessFlag", "isOa", "openAccess", "isOpenAccess"]
        for field in flag_fields:
            if field in record:
                value = record.get(field)
                if isinstance(value, str):
                    normalized = value.lower()
                    if "open" in normalized:
                        is_open_access = True
                    elif any(k in normalized for k in ("denied", "closed", "subscription")):
                        is_open_access = False
                else:
                    is_open_access = bool(value) if value is not None else None
                if is_open_access is not None:
                    break

        access_type = record.get("accessType") or record.get("accessType_s") or record.get("accessTypeIcon")
        if is_open_access is None and isinstance(access_type, str):
            normalized = access_type.lower()
            if "open" in normalized:
                is_open_access = True
            elif any(k in normalized for k in ("denied", "closed", "subscription")):
                is_open_access = False

        pdf_url = record.get("pdfLink") or record.get("htmlLink") or record.get("fullTextLink")
        if isinstance(pdf_url, list):
            pdf_url = pdf_url[0] if pdf_url else None

        if pdf_url and pdf_url.startswith('/'):
            pdf_url = f"https://ieeexplore.ieee.org{pdf_url}"

        if not pdf_url and article_number and is_open_access:
            pdf_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={article_number}"

        return is_open_access, pdf_url

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

        Las cookies se mantienen guardadas en disco para ejecuciones futuras.
        """
        logger.info("IeeeConnector cerrado (sesión guardada en disco)")
