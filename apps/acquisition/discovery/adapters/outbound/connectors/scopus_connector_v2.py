"""
Scopus Connector v2 - API JSON Based usando Playwright.

DIFERENCIAS CON V1:
- V1: Playwright → HTML → BeautifulSoup (lento, frágil)
- V2: Playwright → page.request API → JSON APIs (rápido, confiable)

APIs USADAS:
- POST /api/documents/search → Resultados (title, doi, authors, year, eid)
- POST /gateway/documents/abstracts/retrieve → Abstracts

VENTAJAS:
- ✅ Más rápido (JSON vs HTML parsing)
- ✅ Más confiable (no depende de selectores CSS)
- ✅ Datos completos (DOI + Abstract)

NOTA: Las APIs de Scopus solo funcionan dentro del contexto de Playwright,
no se pueden llamar con requests directamente (dan 403 Forbidden).
"""
import logging
import time
import random
import json
import re
from typing import Dict, List, Any, Generator
from playwright.sync_api import sync_playwright, Page

logger = logging.getLogger(__name__)


class ScopusConnectorV2:
    """
    Conector para Scopus usando APIs JSON internas (vía Playwright).

    Flujo:
    1. Abrir navegador con Playwright
    2. Autenticar vía EZproxy
    3. Usar page.request.post() para llamar APIs JSON
    4. Normalizar y retornar
    """

    # URLs
    SCOPUS_VIA_EZPROXY = "https://bvirtual.epn.edu.ec/login?url=http://www.scopus.com"
    SEARCH_API = "https://www.scopus.com/api/documents/search"
    ABSTRACTS_API = "https://www.scopus.com/gateway/documents/abstracts/retrieve"

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
        Busca en Scopus usando APIs JSON.

        Args:
            query: Término de búsqueda
            max_results: Máximo de resultados

        Yields:
            Dict normalizado
        """
        logger.info(f"Buscando en Scopus: '{query}' (max: {max_results})")

        with sync_playwright() as p:
            # Lanzar navegador
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

                # Buscar usando API
                results = list(self._search_and_extract(page, query, max_results))

                # Yield resultados
                for result in results:
                    yield result

            finally:
                browser.close()

        logger.info("Búsqueda completada")

    def _authenticate(self, page: Page) -> None:
        """
        Autentica en Scopus vía EZproxy.

        Args:
            page: Página de Playwright
        """
        page.goto(self.SCOPUS_VIA_EZPROXY, wait_until="networkidle", timeout=60000)
        time.sleep(2)

        current_url = page.url

        # Si ya estamos en Scopus, no necesitamos autenticar
        if "scopus.com" in current_url:
            logger.info("✓ Ya autenticado (acceso directo)")
            return

        # Buscar formulario de login
        logger.info("Llenando formulario de login...")

        # Buscar campo de usuario
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
        page.wait_for_url("**/scopus.com/**", timeout=30000)

        logger.info("✓ Autenticación exitosa")

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
            scopus_query = f"TITLE-ABS-KEY({query})"

            # Payload para la búsqueda
            search_payload = {
                "query": scopus_query,
                "documentClassificationEnum": "primary",
                "facetMaxCount": 7,
                "includeFacets": [
                    "pubyr", "subjabbr", "subtype", "lang",
                    "exactkeywords", "affilctry", "srctype"
                ]
            }

            logger.debug(f"POST {self.SEARCH_API}")

            # Hacer request usando Playwright's request API
            response = page.request.post(
                self.SEARCH_API,
                data=json.dumps(search_payload),
                headers={"Content-Type": "application/json"}
            )

            if not response.ok:
                raise Exception(f"Search API error: {response.status} {response.status_text}")

            data = response.json()

            # Extraer items
            items = data.get('items', [])
            total_count = data.get('metadata', {}).get('totalCount', 0)

            logger.info(f"✓ Obtenidos {len(items)} resultados (total: {total_count:,})")

            if not items:
                logger.warning("No se encontraron resultados")
                return []

            # Limitar a max_results
            items = items[:max_results]

            # Obtener abstracts en batch
            abstracts_map = self._fetch_abstracts(page, [item.get('eid') for item in items], scopus_query)

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
        query: str
    ) -> Dict[str, str]:
        """
        Obtiene abstracts usando API /gateway/documents/abstracts/retrieve.

        Args:
            page: Página autenticada de Playwright
            eids: Lista de EIDs
            query: Query original

        Returns:
            Dict mapeando eid → abstract_text
        """
        try:
            # Payload para abstracts
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
                self.ABSTRACTS_API,
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
        Normaliza resultado de la API.

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

        return {
            'title': title,
            'link': link,
            'doi': doi,
            'source': 'Scopus',
            'year': year,
            'authors': authors,
            'abstract': abstract
        }

    def close(self):
        """Cierra recursos."""
        logger.info("ScopusConnectorV2 cerrado")
