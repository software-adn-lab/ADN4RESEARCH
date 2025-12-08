"""
IEEE Playwright scraper - Internal implementation detail.

This module contains the legacy Playwright-based scraping implementation
for IEEE Xplore. It is used internally by IeeeWebStrategy and should not
be imported directly by external code.

This is an implementation detail that may be refactored or replaced in
the future without affecting the public API.
"""
from typing import Iterable, Dict, Any, Optional
from playwright.sync_api import sync_playwright, Page, BrowserContext
import time
import json
import logging
import re

logger = logging.getLogger(__name__)


class IeeePlaywrightConnector:
    """
    Conector para IEEE Xplore vía EZproxy institucional usando Playwright.

    No requiere API key; funciona con acceso institucional web.
    Abre navegador en cada búsqueda, por lo que es adecuado para pruebas
    y debugging más que para uso en producción.
    """

    EZPROXY_LOGIN_URL = "https://bvirtual.epn.edu.ec/login"
    IEEE_VIA_EZPROXY = "https://bvirtual.epn.edu.ec/login?url=http://ieeexplore.ieee.org/Xplore/home.jsp"
    IEEE_SEARCH_URL = "https://ieeexplore.ieee.org/search/searchresult.jsp"

    def __init__(
        self,
        username: str,
        password: str,
        headless: bool = True,
        timeout: int = 30000,
        rate_limit: float = 2.0
    ):
        """
        Args:
            username: Correo institucional EPN
            password: Contraseña institucional
            headless: Ejecutar navegador sin ventana visible
            timeout: Timeout en milisegundos para operaciones
            rate_limit: Segundos de espera entre búsquedas
        """
        self.username = username
        self.password = password
        self.headless = headless
        self.timeout = timeout
        self.rate_limit = rate_limit

        self._playwright = None
        self._browser = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._authenticated = False

    def _start_browser(self):
        """Inicia el navegador Playwright."""
        if self._playwright is None:
            logger.info("Iniciando Playwright...")
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=self.headless,
                args=['--start-maximized'] if not self.headless else []
            )
            self._context = self._browser.new_context(
                viewport=None if not self.headless else {'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            self._page = self._context.new_page()
            logger.info("Navegador iniciado")

    def _stop_browser(self):
        """Detiene el navegador y libera recursos."""
        if self._page:
            self._page.close()
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None
        self._authenticated = False

        logger.info("Navegador cerrado")

    def _authenticate(self):
        """
        Autentica en EZproxy de la universidad.

        Requiere estar en la red de la universidad o conectado a la VPN institucional.
        """
        if self._authenticated:
            return

        logger.info(f"Autenticando como {self.username}...")

        try:
            self._page.goto(
                self.IEEE_VIA_EZPROXY,
                wait_until='networkidle',
                timeout=self.timeout
            )

            time.sleep(2)

            current_url = self._page.url

            if "ieeexplore.ieee.org" in current_url:
                logger.info("Sesión activa detectada (sin login necesario)")
                self._authenticated = True
                return

            logger.info("Buscando formulario de login...")

            username_field = None
            password_field = None

            username_selectors = [
                'input[name="user"]',
                'input[name="username"]',
                'input[name="email"]',
                'input[type="email"]',
                'input[id="username"]'
            ]

            for selector in username_selectors:
                try:
                    username_field = self._page.query_selector(selector)
                    if username_field:
                        logger.info(f"Campo usuario detectado: {selector}")
                        break
                except Exception:
                    continue

            password_field = self._page.query_selector('input[type="password"]')

            if not username_field or not password_field:
                raise Exception("No se encontró formulario de login")

            logger.info("Rellenando credenciales...")
            username_field.fill(self.username)
            password_field.fill(self.password)

            submit_button = None
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Sign In")',
                'button:has-text("Login")',
                'button:has-text("Ingresar")'
            ]

            for selector in submit_selectors:
                try:
                    submit_button = self._page.query_selector(selector)
                    if submit_button:
                        break
                except Exception:
                    continue

            if submit_button:
                logger.info("Enviando formulario de login...")
                submit_button.click()
            else:
                password_field.press('Enter')

            logger.info("Esperando resultado de autenticación...")
            time.sleep(5)

            current_url = self._page.url
            if "ieeexplore.ieee.org" in current_url or "IEEE" in self._page.title():
                logger.info("Autenticación exitosa")
                self._authenticated = True
            else:
                raise Exception(f"Autenticación falló. URL actual: {current_url}")

        except Exception as e:
            logger.error(f"Error en autenticación: {e}")
            raise

    def search(self, query: str, max_results: int = 50) -> Iterable[Dict[str, Any]]:
        """
        Busca en IEEE Xplore.

        Args:
            query: Término de búsqueda
            max_results: Máximo de resultados a retornar

        Yields:
            Diccionarios con estructura:
            {
                'title': str,
                'link': str,
                'doi': str | None,
                'source': 'IEEE Xplore',
                'year': int | None,
                'authors': list[str],
                'abstract': str | None,
                'is_open_access': bool | None,
                'pdf_url': str | None
            }
        """
        try:
            if not self._page:
                self._start_browser()

            if not self._authenticated:
                self._authenticate()

            logger.info(f"Buscando en IEEE: '{query}' (max: {max_results})")

            search_url = f"{self.IEEE_SEARCH_URL}?queryText={query}"
            logger.info(f"Navegando a: {search_url}")
            self._page.goto(search_url, wait_until='load', timeout=self.timeout * 2)
            time.sleep(2)

            logger.info("Invocando endpoint /rest/search...")
            try:
                api_url = "https://ieeexplore.ieee.org/rest/search"
                payload = {
                    "queryText": query,
                    "highlight": True,
                    "returnFacets": ["ALL"],
                    "returnType": "SEARCH",
                    "matchPubs": True,
                    "pageNumber": 1,
                    "rowsPerPage": min(max_results, 100)
                }

                response = self._page.request.post(
                    api_url,
                    data=json.dumps(payload),
                    headers={"Content-Type": "application/json"}
                )

                if response.ok:
                    data = response.json()
                    records = data.get('records', [])
                    logger.info(
                        "API /rest/search retornó %s resultados (total: %s)",
                        len(records),
                        data.get('totalRecords', 0),
                    )

                    for i, record in enumerate(records):
                        if i >= max_results:
                            break
                        yield self._normalize_record(record)

                    logger.info(
                        "Resultados retornados: %s",
                        min(len(records), max_results),
                    )
                else:
                    logger.warning(f"API /rest/search falló: {response.status}")
                    raise Exception(f"API error: {response.status}")

            except Exception as api_error:
                logger.warning(f"Error en API directa: {api_error}")
                logger.warning("Usando scraping HTML como fallback...")
                yield from self._scrape_html_results(max_results)

            time.sleep(self.rate_limit)

        except Exception as e:
            logger.error(f"Error en búsqueda IEEE: {e}")
            raise

    def _normalize_record(self, record: Dict) -> Dict[str, Any]:
        """Normaliza un registro devuelto por /rest/search al contrato esperado."""
        article_number = record.get('articleNumber', '')
        is_open_access, pdf_url = self._extract_access_info(record, article_number)

        authors: list[str] = []
        authors_data = record.get('authors', [])
        for author in authors_data:
            if isinstance(author, dict):
                name = (
                    author.get('preferredName') or
                    author.get('fullName') or
                    author.get('name') or
                    author.get('normalizedName', '')
                )
                if name:
                    authors.append(name)
            elif isinstance(author, str):
                authors.append(author)

        return {
            'title': record.get('articleTitle', 'N/A'),
            'link': f"https://ieeexplore.ieee.org/document/{article_number}" if article_number else '',
            'doi': record.get('doi'),
            'source': 'IEEE Xplore',
            'year': record.get('publicationYear'),
            'authors': authors,
            'abstract': record.get('abstract', '').strip() if record.get('abstract') else None,
            'is_open_access': is_open_access,
            'pdf_url': pdf_url,
        }

    def _scrape_html_results(self, max_results: int) -> Iterable[Dict[str, Any]]:
        """
        Fallback: scraping HTML de la página de resultados
        si el endpoint /rest/search no está disponible.
        """
        logger.info("Iniciando scraping HTML de resultados...")

        time.sleep(3)

        result_containers = self._page.query_selector_all('.List-results-items')

        if not result_containers:
            result_containers = self._page.query_selector_all('[class*="result-item"]')

        if not result_containers:
            result_containers = self._page.query_selector_all('.result-item-align')

        count = 0
        for container in result_containers:
            if count >= max_results:
                break

            try:
                title_elem = container.query_selector(
                    'a.fw-bold, h2 a, h3 a, .result-item-title a'
                )
                title = title_elem.inner_text().strip() if title_elem else 'N/A'

                link = ''
                if title_elem:
                    href = title_elem.get_attribute('href')
                    if href:
                        link = (
                            f'https://ieeexplore.ieee.org{href}'
                            if href.startswith('/')
                            else href
                        )

                article_number = ''
                if link:
                    match = re.search(r'/document/(\\d+)', link)
                    if match:
                        article_number = match.group(1)

                doi = None
                doi_selectors = [
                    'a[href*="doi.org"]',
                    '[class*="doi"]',
                    ':text("DOI:")'
                ]
                for sel in doi_selectors:
                    try:
                        doi_elem = container.query_selector(sel)
                        if doi_elem:
                            doi_text = doi_elem.inner_text().strip()
                            doi_match = re.search(r'10\.\d{4,}/[^\s]+', doi_text)
                            if doi_match:
                                doi = doi_match.group(0)
                                break
                    except Exception:
                        continue

                authors: list[str] = []
                authors_elem = container.query_selector('.author, [class*="authors"]')
                if authors_elem:
                    authors_text = authors_elem.inner_text().strip()
                    if ';' in authors_text:
                        authors = [a.strip() for a in authors_text.split(';') if a.strip()]
                    elif ',' in authors_text:
                        authors = [a.strip() for a in authors_text.split(',') if a.strip()]
                    else:
                        authors = [authors_text] if authors_text else []

                year = None
                year_elem = container.query_selector('[class*="year"], [class*="date"]')
                if year_elem:
                    year_text = year_elem.inner_text().strip()
                    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', year_text)
                    if year_match:
                        year = int(year_match.group(1))

                abstract = None
                abstract_elem = container.query_selector(
                    '[class*="abstract"], [class*="snippet"]'
                )
                if abstract_elem:
                    abstract = abstract_elem.inner_text().strip()

                is_open_access = None
                access_elem = container.query_selector(
                    '.xpl-access-type-icon, '
                    '[class*="access-type" i], '
                    '[class*="open-access" i]'
                )
                if access_elem:
                    access_text = (access_elem.inner_text() or "").lower()
                    access_attr = (access_elem.get_attribute('title') or "").lower()
                    combined = f"{access_text} {access_attr}"
                    if 'open' in combined:
                        is_open_access = True
                    elif any(
                        k in combined for k in ('denied', 'closed', 'subscription')
                    ):
                        is_open_access = False

                pdf_url = None
                pdf_elem = container.query_selector(
                    'a[href*="stamp/stamp.jsp"], '
                    'a[title*="PDF" i], '
                    'a.icon-pdf, '
                    'a[href*="/pdf/"]'
                )
                if pdf_elem:
                    href = pdf_elem.get_attribute('href')
                    if href:
                        pdf_url = (
                            f'https://ieeexplore.ieee.org{href}'
                            if href.startswith('/')
                            else href
                        )

                if not pdf_url and article_number and is_open_access:
                    pdf_url = (
                        "https://ieeexplore.ieee.org/stamp/stamp.jsp"
                        f"?tp=&arnumber={article_number}"
                    )

                yield {
                    'title': title,
                    'link': link,
                    'doi': doi,
                    'source': 'IEEE Xplore',
                    'year': year,
                    'authors': authors,
                    'abstract': abstract,
                    'is_open_access': is_open_access,
                    'pdf_url': pdf_url,
                }

                count += 1
            except Exception as e:
                logger.warning(f"Error extrayendo resultado HTML: {e}")
                continue

        logger.info("HTML scraping completado (%s resultados)", count)

    def close(self):
        """Cierra el navegador y libera recursos."""
        self._stop_browser()

    def __enter__(self):
        """Soporte para uso como context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Soporte para uso como context manager."""
        self.close()

    def _extract_access_info(
        self,
        record: Dict[str, Any],
        article_number: str
    ) -> tuple[Optional[bool], Optional[str]]:
        """
        Infere acceso abierto y URL del PDF desde el registro devuelto por /rest/search.
        """
        is_open_access: Optional[bool] = None
        for field in ["openAccessFlag", "isOa", "openAccess", "isOpenAccess"]:
            if field in record:
                value = record.get(field)
                if isinstance(value, str):
                    normalized = value.lower()
                    if "open" in normalized:
                        is_open_access = True
                    elif any(
                        k in normalized
                        for k in ("denied", "closed", "subscription")
                    ):
                        is_open_access = False
                else:
                    is_open_access = bool(value) if value is not None else None
                if is_open_access is not None:
                    break

        access_type = (
            record.get("accessType")
            or record.get("accessType_s")
            or record.get("accessTypeIcon")
            or record.get("accessType_x")
        )
        if is_open_access is None and isinstance(access_type, str):
            normalized = access_type.lower()
            if "open" in normalized:
                is_open_access = True
            elif any(k in normalized for k in ("denied", "closed", "subscription")):
                is_open_access = False

        pdf_url = (
            record.get("pdfLink")
            or record.get("htmlLink")
            or record.get("fullTextLink")
        )
        if isinstance(pdf_url, list):
            pdf_url = pdf_url[0] if pdf_url else None

        if pdf_url and isinstance(pdf_url, str) and pdf_url.startswith('/'):
            pdf_url = f"https://ieeexplore.ieee.org{pdf_url}"

        if not pdf_url and article_number and is_open_access:
            pdf_url = (
                "https://ieeexplore.ieee.org/stamp/stamp.jsp"
                f"?tp=&arnumber={article_number}"
            )

        return is_open_access, pdf_url
