"""
Scopus Playwright Connector - Scraping basado en APIs internas de Scopus.

Este conector se usa como FALLBACK cuando el API oficial de Elsevier no está disponible.
Usa Playwright para autenticar vía EZproxy y luego llama APIs JSON internas de Scopus.

APIs USADAS:
- POST /api/documents/search/facets -> Resultados (title, doi, authors, year, eid)
- POST /gateway/documents/abstracts/retrieve -> Abstracts

NOTA: Las APIs de Scopus solo funcionan dentro del contexto de Playwright,
no se pueden llamar con requests directamente (dan 403 Forbidden).
"""
import logging
import time
import json
import re
from typing import Dict, List, Any, Generator, Tuple
from urllib.parse import urlparse
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright, Page

logger = logging.getLogger(__name__)


class ScopusPlaywrightConnector:
    """
    Conector para Scopus usando APIs JSON internas (vía Playwright).

    Se usa como fallback cuando el API oficial de Elsevier no está disponible.

    Flujo:
    1. Abrir navegador con Playwright
    2. Autenticar vía EZproxy
    3. Usar page.request.post() para llamar APIs JSON internas
    4. Normalizar y retornar
    """

    # URLs
    SCOPUS_VIA_EZPROXY = "https://bvirtual.epn.edu.ec/login?url=http://www.scopus.com/"
    DEFAULT_PROXY_BASE = "https://bvirtual.epn.edu.ec:2057"
    SEARCH_PATH = "/api/documents/search/facets"
    ABSTRACTS_PATH = "/gateway/documents/abstracts/retrieve"

    def __init__(
        self,
        username: str,
        password: str,
        headless: bool = True
    ):
        """
        Args:
            username: Usuario EPN
            password: Contraseña EPN
            headless: Navegador sin interfaz
        """
        self.username = username
        self.password = password
        self.headless = headless

    def search(
        self,
        query: str,
        max_results: int = 25
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Busca en Scopus usando APIs JSON internas.

        Args:
            query: Término de búsqueda
            max_results: Máximo de resultados

        Yields:
            Dict normalizado con title, link, doi, source, year, authors, abstract
        """
        logger.info(f"[Playwright] Buscando en Scopus: '{query}' (max: {max_results})")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                args=['--disable-blink-features=AutomationControlled']
            )

            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                viewport={'width': 1920, 'height': 1080}
            )

            page = context.new_page()

            try:
                # Autenticar
                self._authenticate(page)

                # Buscar usando API interna
                results = list(self._search_and_extract(page, query, max_results))

                for result in results:
                    yield result

            finally:
                browser.close()

        logger.info("[Playwright] Búsqueda completada")

    def _authenticate(self, page: Page) -> None:
        """
        Autentica en Scopus vía EZproxy.

        Args:
            page: Página de Playwright
        """
        page.goto(self.SCOPUS_VIA_EZPROXY, wait_until="load", timeout=60000)
        time.sleep(2)

        current_url = page.url

        # Si ya estamos en Scopus, no necesitamos autenticar
        if "scopus.com" in current_url:
            logger.info("✓ Ya autenticado (acceso directo)")
            return

        # Buscar formulario de login
        logger.info("Llenando formulario de login...")

        username_selectors = [
            'input[name="user"]',
            'input[name="username"]',
            'input[type="email"]',
            'input[id="username"]'
        ]

        username_field = None
        for selector in username_selectors:
            try:
                username_field = page.query_selector(selector)
                if username_field:
                    break
            except:
                continue

        if not username_field:
            raise Exception("No se encontró campo de usuario")

        # Llenar credenciales
        username_field.fill(self.username)
        time.sleep(0.5)

        password_field = page.query_selector('input[type="password"]')
        if not password_field:
            raise Exception("No se encontró campo de contraseña")

        password_field.fill(self.password)
        time.sleep(0.5)

        # Submit
        password_field.press('Enter')

        # Esperar redirección
        logger.info("Esperando autenticación...")
        page.wait_for_load_state("networkidle", timeout=60000)
        current_url = page.url

        if "login" in current_url:
            raise Exception(
                "Autenticación Scopus fallida o bloqueada por reCAPTCHA (sigues en la página de login)"
            )

        # Refrescar cookies clave que activa la API JSON (scopus-proxy)
        parsed = urlparse(current_url)
        if parsed.hostname and parsed.hostname.endswith("bvirtual.epn.edu.ec"):
            base = f"{parsed.scheme}://{parsed.netloc}"
            self._set_scopus_proxy_cookie(page, base)

        logger.info("✓ Autenticación exitosa")

    def _set_scopus_proxy_cookie(self, page: Page, base: str) -> None:
        """
        Marca la cookie scopus-proxy=true (vista en tráfico real) para habilitar las APIs JSON.
        """
        try:
            page.request.post(
                f"{base}/cookies/set.uri",
                data=urlencode(
                    {
                        "name": "scopus-proxy",
                        "value": "true",
                        "expiration": "86400000",  # 1 día en ms (mismo que tráfico capturado)
                    }
                ),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                },
            )
            logger.debug("✓ Cookie scopus-proxy configurada")
        except Exception as e:
            logger.debug(f"No se pudo setear scopus-proxy: {e}")

    def _resolve_api_urls(self, page: Page) -> Tuple[str, str]:
        """
        Construye las URLs de API usando el host actual (incluye puerto de EZproxy).

        Args:
            page: Página autenticada

        Returns:
            (search_api_url, abstracts_api_url)
        """
        parsed = urlparse(page.url)
        base = self.DEFAULT_PROXY_BASE

        if parsed.scheme and parsed.netloc:
            hostname = parsed.hostname or ""

            if hostname.endswith("bvirtual.epn.edu.ec"):
                # Preferir el puerto proxy (2057) si no viene en la URL
                base = self.DEFAULT_PROXY_BASE if parsed.port is None else f"{parsed.scheme}://{parsed.netloc}"
            elif "scopus.com" in hostname:
                # La sesión sigue autenticada vía EZproxy, pero las APIs responden en el host proxy
                base = self.DEFAULT_PROXY_BASE
            else:
                base = f"{parsed.scheme}://{parsed.netloc}"

        search_api = f"{base}{self.SEARCH_PATH}"
        abstracts_api = f"{base}{self.ABSTRACTS_PATH}"

        return search_api, abstracts_api

    def _search_and_extract(
        self,
        page: Page,
        query: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta búsqueda usando API /api/documents/search.

        Args:
            page: Página autenticada de Playwright
            query: Término de búsqueda
            max_results: Número máximo de resultados

        Returns:
            Lista de resultados normalizados
        """
        try:
            # Construir query de Scopus
            scopus_query = query if "TITLE-ABS-KEY" in query else f"TITLE-ABS-KEY({query})"

            search_api, abstracts_api = self._resolve_api_urls(page)

            # Payload para la búsqueda
            search_payload = {
                "query": scopus_query,
                "documentClassificationEnum": "primary",
                "facetMaxCount": 7,
                "includeFacets": [
                    "pubyr", "subjabbr", "subtype", "lang",
                    "exactkeywords", "affilctry", "srctype",
                    "exactsrctitle", "prefnameauid", "pubstage",
                    "afid", "fundsponsor", "freetoread"
                ],
                "itemcount": max_results,
                "offset": 0
            }

            logger.debug(f"POST {search_api}")

            response = page.request.post(
                search_api,
                data=json.dumps(search_payload),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )

            # Verificar respuesta
            headers = response.headers if isinstance(response.headers, dict) else response.headers()
            content_type = (headers.get("content-type") or "").lower()
            status_code = response.status if hasattr(response, "status") else None

            if not response.ok or "json" not in content_type:
                logger.error(f"Scopus API interna: Error {status_code}")
                try:
                    response_text = response.text()
                    with open("debug_scopus_playwright_error.html", "w", encoding="utf-8") as f:
                        f.write(response_text)
                    logger.info("Error guardado en debug_scopus_playwright_error.html")
                except Exception as e:
                    logger.error(f"No se pudo guardar debug: {e}")
                raise Exception(f"Search API error: {status_code}")

            data = response.json()

            # Extraer items
            items = (
                data.get('items')
                or data.get('documents')
                or data.get('results', {}).get('documents')
                or []
            )
            metadata = data.get('metadata') or data.get('results', {}).get('metadata') or {}
            total_count = metadata.get('totalCount', 0) or len(items)

            logger.info(f"✓ Obtenidos {len(items)} resultados (total: {total_count:,})")

            if not items:
                return []

            # Limitar a max_results
            items = items[:max_results]

            # Obtener abstracts
            abstracts_map = self._fetch_abstracts(
                page,
                [item.get('eid') for item in items],
                scopus_query,
                abstracts_api
            )

            # Normalizar resultados
            results = []
            for item in items:
                eid = item.get('eid')
                abstract = abstracts_map.get(eid)
                result = self._normalize_result(item, abstract)
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Error en API search: {e}")
            raise

    def _fetch_abstracts(
        self,
        page: Page,
        eids: List[str],
        query: str,
        abstracts_api: str
    ) -> Dict[str, str]:
        """
        Obtiene abstracts usando API /gateway/documents/abstracts/retrieve.

        Args:
            page: Página autenticada de Playwright
            eids: Lista de EIDs
            query: Query original

        Returns:
            Dict mapeando eid -> abstract_text
        """
        try:
            abstracts_payload = {
                "eids": eids,
                "query": query,
                "documentClassification": "primary",
                "resultSet": {
                    "itemCount": len(eids),
                    "offset": 0
                },
                "enableHighlight": True
            }

            logger.debug(f"Fetching abstracts for {len(eids)} documents...")

            response = page.request.post(
                abstracts_api,
                data=json.dumps(abstracts_payload),
                headers={"Content-Type": "application/json"}
            )

            if not response.ok:
                logger.warning(f"Abstracts API error: {response.status}")
                return {}

            data = response.json()

            # Parsear abstracts
            abstracts = data.get('abstracts', [])
            abstracts_map = {}

            for abstract_item in abstracts:
                eid = abstract_item.get('eid')
                abstract_html = abstract_item.get('abstractHtml', '')

                if isinstance(abstract_html, list):
                    abstract_html = ' '.join(abstract_html)

                # Limpiar HTML tags
                abstract_text = re.sub(r'<[^>]+>', '', abstract_html)
                abstract_text = abstract_text.strip()

                if abstract_text:
                    abstracts_map[eid] = abstract_text

            logger.debug(f"✓ Obtenidos {len(abstracts_map)} abstracts")

            return abstracts_map

        except Exception as e:
            logger.warning(f"Error obteniendo abstracts: {e}")
            return {}

    def _normalize_result(
        self,
        item: Dict,
        abstract: str = None
    ) -> Dict[str, Any]:
        """
        Normaliza resultado de la API interna.

        Args:
            item: Item del response
            abstract: Abstract obtenido

        Returns:
            Dict normalizado
        """
        # Título
        title = item.get('title', 'N/A')

        # DOI
        doi = item.get('doi')

        # Año
        year = item.get('pubYear')
        if year:
            try:
                year = int(year)
            except:
                year = None

        # Autores
        authors_data = item.get('authors', [])
        authors = []
        for author in authors_data:
            preferred_name = author.get('preferredName', {})
            full_name = preferred_name.get('full', '').strip()
            if full_name:
                authors.append(full_name)

        # Link
        link = None
        links = item.get('links', [])
        for link_item in links:
            if link_item.get('label') == 'View at Publisher':
                link = link_item.get('href')
                break

        # Si no hay link, construir desde EID
        if not link:
            eid = item.get('eid', '')
            if eid:
                link = f"https://www.scopus.com/record/display.uri?eid={eid}&origin=resultslist"

        # Extraer información de Open Access
        # Las APIs internas de Scopus también incluyen OA flags
        is_open_access = None
        openaccess_flag = item.get('openaccessFlag') or item.get('openAccessFlag')
        openaccess_str = item.get('openaccess') or item.get('openAccess')

        if isinstance(openaccess_flag, bool):
            is_open_access = openaccess_flag
        elif isinstance(openaccess_str, str):
            normalized = openaccess_str.lower()
            if normalized in ('1', 'true', 'yes'):
                is_open_access = True
            elif normalized in ('0', 'false', 'no'):
                is_open_access = False
        elif openaccess_str in (1, True):
            is_open_access = True
        elif openaccess_str in (0, False):
            is_open_access = False

        # PDF URL: Si es OA y tiene DOI, usar URL del DOI
        pdf_url = None
        if is_open_access and doi:
            pdf_url = f"https://doi.org/{doi}"

        return {
            'title': title,
            'link': link,
            'doi': doi,
            'source': 'Scopus',
            'year': year,
            'authors': authors,
            'abstract': abstract,
            # Open Access (Feature 4 integration)
            'is_open_access': is_open_access,
            'pdf_url': pdf_url
        }

    def close(self):
        """Cierra recursos."""
        logger.info("ScopusPlaywrightConnector cerrado")
