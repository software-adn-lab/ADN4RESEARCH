"""
Conector para Scopus (Elsevier).

Scopus NO tiene API REST pública como IEEE.
Este conector usa Playwright para:
1. Autenticar via EZproxy (obtener cookies)
2. Navegar a resultados de búsqueda
3. Extraer datos del HTML

IMPORTANTE:
- Scopus está protegido por Cloudflare
- NO se puede usar requests directo (da 403)
- DEBE usar Playwright para TODO
"""
import logging
import time
from typing import Dict, List, Any, Generator
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from bs4 import BeautifulSoup
import re
import json

logger = logging.getLogger(__name__)


class ScopusConnector:
    """
    Conector para búsquedas en Scopus vía EZproxy.

    Características:
    - Usa Playwright para navegar (bypass Cloudflare)
    - Autentica automáticamente vía EZproxy si es necesario
    - Parsea HTML para extraer resultados
    - Normaliza datos al formato estándar

    Uso:
        connector = ScopusConnector(username, password)
        results = list(connector.search("machine learning", max_results=10))
    """

    # URLs
    SCOPUS_VIA_EZPROXY = "https://bvirtual.epn.edu.ec/login?url=http://www.scopus.com"
    SCOPUS_HOME = "https://www.scopus.com/pages/home"
    SCOPUS_SEARCH_URL = "https://www.scopus.com/results/results.uri"

    def __init__(
        self,
        username: str,
        password: str,
        headless: bool = True
    ):
        """
        Inicializa el conector de Scopus.

        Args:
            username: Usuario EPN
            password: Contraseña EPN
            headless: Si True, navegador sin interfaz gráfica
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
        Busca artículos en Scopus.

        Args:
            query: Término de búsqueda
            max_results: Número máximo de resultados a retornar

        Yields:
            Dict con datos del artículo normalizado

        Example:
            >>> connector = ScopusConnector("user@epn.edu.ec", "password")
            >>> for article in connector.search("machine learning", max_results=10):
            ...     print(article['title'])
        """
        logger.info(f"Iniciando búsqueda en Scopus: '{query}' (max: {max_results})")

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
                logger.info("Autenticando en Scopus...")
                self._authenticate(page)

                # Buscar
                logger.info(f"Ejecutando búsqueda: {query}")
                results = self._search_and_extract(page, query, max_results)

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

        Raises:
            Exception: Si falla la autenticación
        """
        # Navegar a Scopus via EZproxy
        page.goto(self.SCOPUS_VIA_EZPROXY, wait_until="networkidle", timeout=60000)
        time.sleep(2)

        current_url = page.url

        # Si ya estamos en Scopus, no necesitamos autenticar
        if "scopus.com" in current_url:
            logger.info("✓ Ya autenticado (acceso directo por IP o cookies)")
            return

        # Buscar formulario de login
        logger.info("Llenando formulario de login...")

        # Buscar campo de usuario
        username_field = None
        username_selectors = [
            'input[name="user"]',
            'input[name="username"]',
            'input[type="email"]',
            'input[id="username"]'
        ]

        for selector in username_selectors:
            try:
                username_field = page.query_selector(selector)
                if username_field:
                    break
            except:
                continue

        if not username_field:
            raise Exception("No se encontró campo de usuario en formulario de login")

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

        # Esperar redirección a Scopus
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
        Ejecuta búsqueda y extrae resultados usando selectores de Playwright.

        Args:
            page: Página de Playwright
            query: Término de búsqueda
            max_results: Número máximo de resultados

        Returns:
            Lista de artículos normalizados
        """
        # Construir URL de búsqueda
        search_params = {
            "st1": query,
            "st2": "",
            "s": f"TITLE-ABS-KEY({query})",
            "limit": str(min(max_results, 200)),  # Scopus max 200 por página
            "origin": "searchbasic",
            "sort": "plf-f",  # newest first
            "src": "s",
            "sot": "b",
            "sdt": "b"
        }

        # Construir query string
        query_string = "&".join([f"{k}={v}" for k, v in search_params.items()])
        search_url = f"{self.SCOPUS_SEARCH_URL}?{query_string}"

        logger.debug(f"Navegando a: {search_url}")

        # Navegar a resultados
        page.goto(search_url, wait_until="networkidle", timeout=60000)

        # Esperar que cargue el Web Component principal
        logger.debug("Esperando a que cargue el Web Component...")

        try:
            page.wait_for_selector('document-search-results-page', timeout=15000, state="attached")
            logger.debug("✓ Web Component cargado")
        except:
            logger.warning("No se encontró Web Component, continuando...")

        # Dar tiempo para que JavaScript renderice contenido
        time.sleep(5)

        # Extraer resultados usando selectores de Playwright (NO BeautifulSoup)
        logger.debug("Extrayendo resultados del DOM renderizado...")
        results = self._extract_with_playwright(page, max_results)

        logger.info(f"✓ Extraídos {len(results)} resultados")

        return results

    def _extract_with_playwright(self, page: Page, max_results: int) -> List[Dict[str, Any]]:
        """
        Extrae resultados usando selectores de Playwright en el DOM renderizado.

        Args:
            page: Página de Playwright
            max_results: Número máximo de resultados

        Returns:
            Lista de artículos normalizados
        """
        results = []

        # Selectores posibles para items de resultado
        # Scopus usa TABLA para mostrar resultados
        # Los data-testid están DENTRO de los <tr>, no en ellos
        result_item_selectors = [
            'tr:has([data-testid="author-list"])',  # TR que contiene author-list
            'tbody tr',  # Filas de tabla genéricas
            'table tr',  # Filas de cualquier tabla
        ]

        # Intentar encontrar elementos de resultado
        result_elements = None
        used_selector = None

        for selector in result_item_selectors:
            elements = page.query_selector_all(selector)
            if elements and len(elements) > 0:
                result_elements = elements
                used_selector = selector
                logger.debug(f"✓ Encontrados {len(elements)} elementos con selector: {selector}")
                break

        if not result_elements:
            logger.warning("No se encontraron elementos de resultado con selectores conocidos")

            # Guardar HTML para debugging
            with open('scopus_search_results_debug.html', 'w', encoding='utf-8') as f:
                f.write(page.content())
            logger.debug("HTML guardado en: scopus_search_results_debug.html")

            return []

        # Extraer datos de cada elemento
        logger.debug(f"Extrayendo datos de {len(result_elements)} elementos...")

        for i, elem in enumerate(result_elements[:max_results]):
            try:
                result = self._extract_from_playwright_element(elem)
                if result and result.get('title'):  # Solo agregar si tiene título
                    results.append(result)
                    logger.debug(f"  {i+1}. {result['title'][:60]}...")
            except Exception as e:
                logger.warning(f"Error extrayendo elemento {i}: {e}")
                continue

        return results

    def _extract_from_playwright_element(self, elem) -> Dict[str, Any]:
        """
        Extrae datos de un elemento de Playwright.

        Args:
            elem: ElementHandle de Playwright

        Returns:
            Dict con datos normalizados
        """
        # Título - Scopus usa data-testid o clases específicas
        title = None
        title_selectors = [
            '[data-testid="document-title"] a',  # Link del título
            '[data-testid="document-title"]',
            'a[href*="/record/"]',  # Link a record
            'h2 a',
            'h3 a',
            'td a',  # Link en celda de tabla
            'a',  # Cualquier link como fallback
        ]

        for selector in title_selectors:
            title_elem = elem.query_selector(selector)
            if title_elem:
                title = title_elem.inner_text().strip()
                if title and len(title) > 10:  # Validar que sea título real
                    break

        if not title:
            # Fallback: buscar primer link significativo
            all_links = elem.query_selector_all('a')
            for link in all_links:
                link_text = link.inner_text().strip()
                if link_text and len(link_text) > 20:  # Probablemente un título
                    title = link_text
                    break

        # Autores - Scopus usa data-testid='author-list'
        authors = []
        author_container = elem.query_selector('[data-testid="author-list"]')

        if author_container:
            # Buscar elementos de autor individuales
            author_elems = author_container.query_selector_all('button, a, span[class*="Author"]')
            if author_elems:
                seen_authors = set()  # Evitar duplicados
                for auth_elem in author_elems[:15]:  # Máx 15 para tener margen
                    author_text = auth_elem.inner_text().strip()

                    # Limpiar texto: quitar newlines, comas finales, "and N more..."
                    author_text = author_text.replace('\n', '').replace('\r', '').strip(' ,.')

                    if author_text and 3 < len(author_text) < 100:
                        # Ignorar "and N more..." y "..."
                        if 'more' not in author_text.lower() and author_text != '...':
                            # Evitar duplicados (normalizar para comparar)
                            author_normalized = author_text.lower().strip()
                            if author_normalized not in seen_authors:
                                seen_authors.add(author_normalized)
                                authors.append(author_text)
            else:
                # Si no hay sub-elementos, tomar texto completo y parsear
                author_text = author_container.inner_text().strip()
                authors = self._parse_authors(author_text)

        # Año - Scopus usa data-testid='document-publication-year'
        year = None
        year_elem = elem.query_selector('[data-testid="document-publication-year"]')

        if year_elem:
            year_text = year_elem.inner_text().strip()
            year = self._extract_year(year_text)

        # Si no encontró año con testid, buscar en texto general
        if not year:
            year_selectors = ['[class*="year"]', '[class*="date"]', 'span']
            for selector in year_selectors:
                year_elem = elem.query_selector(selector)
                if year_elem:
                    year_text = year_elem.inner_text().strip()
                    year = self._extract_year(year_text)
                    if year:
                        break

        # DOI
        doi = None
        doi_selectors = [
            'a[href*="doi.org"]',
            '[class*="doi"]',
        ]

        for selector in doi_selectors:
            doi_elem = elem.query_selector(selector)
            if doi_elem:
                # Intentar obtener del href
                href = doi_elem.get_attribute('href')
                if href and 'doi.org' in href:
                    doi_match = re.search(r'10\.\d{4,}/[^\s&]+', href)
                    if doi_match:
                        doi = doi_match.group(0)
                        break

                # Intentar del texto
                doi_text = doi_elem.inner_text().strip()
                doi_match = re.search(r'10\.\d{4,}/[^\s]+', doi_text)
                if doi_match:
                    doi = doi_match.group(0)
                    break

        # Abstract
        abstract = None
        abstract_selectors = [
            '[class*="abstract"]',
            '[class*="Abstract"]',
            '[class*="snippet"]',
        ]

        for selector in abstract_selectors:
            abstract_elem = elem.query_selector(selector)
            if abstract_elem:
                abstract = abstract_elem.inner_text().strip()
                if abstract:
                    break

        # URL - buscar link
        url = None
        link_elem = elem.query_selector('a[href*="/record/"]')
        if not link_elem:
            link_elem = elem.query_selector('h2 a, h3 a')

        if link_elem:
            href = link_elem.get_attribute('href')
            if href:
                if href.startswith('/'):
                    url = f"https://www.scopus.com{href}"
                elif href.startswith('http'):
                    url = href

        return self._normalize_result({
            'title': title,
            'authors': authors,
            'year': year,
            'doi': doi,
            'abstract': abstract,
            'url': url
        })

    def _parse_html(self, html: str) -> List[Dict[str, Any]]:
        """
        Parsea HTML de Scopus y extrae resultados.

        Estrategias (en orden):
        1. Buscar JSON embebido en <script>
        2. Parsear elementos HTML directamente

        Args:
            html: HTML completo de la página

        Returns:
            Lista de artículos normalizados
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Estrategia 1: JSON embebido
        results = self._extract_from_json(soup)
        if results:
            logger.debug(f"Extraídos {len(results)} resultados de JSON embebido")
            return results

        # Estrategia 2: HTML parsing
        results = self._extract_from_html(soup)
        if results:
            logger.debug(f"Extraídos {len(results)} resultados de HTML")
            return results

        logger.warning("No se pudieron extraer resultados del HTML")
        return []

    def _extract_from_json(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extrae resultados de JSON embebido en <script> tags.

        Args:
            soup: BeautifulSoup del HTML

        Returns:
            Lista de artículos normalizados
        """
        script_tags = soup.find_all('script', type='application/json')

        for tag in script_tags:
            if not tag.string:
                continue

            try:
                data = json.loads(tag.string)

                # Buscar array de resultados
                result_keys = ['searchResults', 'results', 'documents', 'entries', 'documentEntries']

                for key in result_keys:
                    if key in data and isinstance(data[key], list):
                        logger.debug(f"Encontrado array '{key}' con {len(data[key])} elementos")
                        return [self._normalize_result(item) for item in data[key]]

            except json.JSONDecodeError:
                continue

        return []

    def _extract_from_html(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extrae resultados parseando elementos HTML directamente.

        Args:
            soup: BeautifulSoup del HTML

        Returns:
            Lista de artículos normalizados
        """
        results = []

        # Selectores posibles para items de resultado
        selectors = [
            'div.result-item',
            'article',
            'li.result-item',
            'div[class*="ResultItem"]',
            'div[class*="documentEntry"]',
        ]

        result_elements = []
        for selector in selectors:
            result_elements = soup.select(selector)
            if result_elements:
                logger.debug(f"Encontrados {len(result_elements)} elementos con selector: {selector}")
                break

        if not result_elements:
            return []

        # Extraer datos de cada elemento
        for elem in result_elements:
            try:
                result = self._extract_from_element(elem)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Error extrayendo elemento: {e}")
                continue

        return results

    def _extract_from_element(self, elem) -> Dict[str, Any]:
        """
        Extrae datos de un elemento HTML de resultado.

        Args:
            elem: BeautifulSoup element

        Returns:
            Dict con datos normalizados
        """
        # Título
        title_elem = elem.select_one('h2, h3, h4, a[class*="title"], [class*="Title"]')
        title = title_elem.get_text(strip=True) if title_elem else "N/A"

        # Autores
        authors_elem = elem.select_one('[class*="author"], [class*="Author"]')
        authors_text = authors_elem.get_text(strip=True) if authors_elem else ""
        authors = self._parse_authors(authors_text)

        # Año
        year_elem = elem.select_one('[class*="year"], [class*="date"]')
        year_text = year_elem.get_text(strip=True) if year_elem else ""
        year = self._extract_year(year_text)

        # DOI
        doi_elem = elem.select_one('[class*="doi"], a[href*="doi.org"]')
        doi = None
        if doi_elem:
            doi_text = doi_elem.get_text(strip=True)
            doi_match = re.search(r'10\.\d{4,}/[^\s]+', doi_text)
            if doi_match:
                doi = doi_match.group(0)

        # Abstract
        abstract_elem = elem.select_one('[class*="abstract"], [class*="Abstract"]')
        abstract = abstract_elem.get_text(strip=True) if abstract_elem else None

        # URL
        link_elem = elem.select_one('a[href*="/record/"]')
        url = None
        if link_elem:
            href = link_elem.get('href', '')
            if href.startswith('/'):
                url = f"https://www.scopus.com{href}"
            else:
                url = href

        return self._normalize_result({
            'title': title,
            'authors': authors,
            'year': year,
            'doi': doi,
            'abstract': abstract,
            'url': url
        })

    def _normalize_result(self, raw_data: Dict) -> Dict[str, Any]:
        """
        Normaliza resultado al formato estándar.

        Args:
            raw_data: Datos crudos extraídos

        Returns:
            Dict normalizado
        """
        return {
            'title': raw_data.get('title', 'N/A'),
            'link': raw_data.get('url') or raw_data.get('link'),
            'doi': raw_data.get('doi'),
            'source': 'Scopus',
            'year': raw_data.get('year') or raw_data.get('publicationYear'),
            'authors': raw_data.get('authors', []),
            'abstract': raw_data.get('abstract')
        }

    def _parse_authors(self, authors_text: str) -> List[str]:
        """
        Parsea string de autores a lista.

        Args:
            authors_text: String con autores (ej: "Smith, J.; Doe, A.")

        Returns:
            Lista de nombres de autores
        """
        if not authors_text:
            return []

        # Separar por comas, punto y coma, etc.
        separators = [';', ',']
        for sep in separators:
            if sep in authors_text:
                authors = [a.strip() for a in authors_text.split(sep)]
                return [a for a in authors if a]

        return [authors_text.strip()]

    def _extract_year(self, text: str) -> int:
        """
        Extrae año de un texto.

        Args:
            text: Texto que contiene año

        Returns:
            Año como entero, o None
        """
        if not text:
            return None

        # Buscar patrón de 4 dígitos entre 1900-2100
        match = re.search(r'\b(19\d{2}|20\d{2}|21\d{2})\b', text)
        if match:
            return int(match.group(1))

        return None

    def close(self):
        """
        Cierra recursos.

        Nota: En esta implementación simple, no hay recursos persistentes.
        """
        logger.info("ScopusConnector cerrado")
