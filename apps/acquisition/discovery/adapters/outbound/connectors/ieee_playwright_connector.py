"""
IEEE Xplore Connector usando SOLO Playwright (sin session manager).

⚠️  NOTA: Este conector es una versión legacy/alternativa.
    Para uso normal, usa IeeeConnector (ieee_connector.py) que:
    - Detecta automáticamente red universitaria
    - Usa session manager con cookies persistentes
    - Es más rápido (no abre navegador en cada búsqueda)

CASOS DE USO de este connector:
- Testing y debugging de autenticación EZproxy
- Referencia de cómo funciona Playwright con IEEE
- Fallback si session manager falla

FUNCIONAMIENTO:
1. Autentica a través de bvirtual.epn.edu.ec (EZproxy) con Playwright
2. Ejecuta búsquedas en IEEE Xplore
3. Captura resultados del endpoint /rest/search
4. Normaliza resultados al contrato esperado

IMPORTANTE: Abre navegador en CADA búsqueda (lento).
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
    Conector para IEEE Xplore vía EZproxy institucional.

    NO requiere API key, funciona con acceso institucional web.
    """

    # URLs
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
        """Inicia el navegador Playwright"""
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
            logger.info("✓ Navegador iniciado")

    def _stop_browser(self):
        """Detiene el navegador"""
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

        logger.info("✓ Navegador cerrado")

    def _authenticate(self):
        """
        Autentica en EZproxy de la universidad.

        IMPORTANTE: Requiere estar en la RED DE LA UNIVERSIDAD
        o conectado a VPN institucional.
        """
        if self._authenticated:
            return

        logger.info(f"Autenticando como {self.username}...")

        try:
            # Ir a IEEE vía EZproxy
            self._page.goto(self.IEEE_VIA_EZPROXY, wait_until='networkidle', timeout=self.timeout)

            time.sleep(2)

            current_url = self._page.url

            # Si ya estamos en IEEE, la sesión ya existe
            if "ieeexplore.ieee.org" in current_url:
                logger.info("✓ Sesión activa detectada (sin login necesario)")
                self._authenticated = True
                return

            # Si no, necesitamos hacer login
            logger.info("Buscando formulario de login...")

            # Intentar encontrar campos de login
            username_field = None
            password_field = None

            # Selectores comunes para EZproxy
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
                        logger.info(f"✓ Campo usuario: {selector}")
                        break
                except:
                    continue

            password_field = self._page.query_selector('input[type="password"]')

            if not username_field or not password_field:
                raise Exception("No se encontró formulario de login")

            # Llenar credenciales
            logger.info("Rellenando credenciales...")
            username_field.fill(self.username)
            password_field.fill(self.password)

            # Buscar botón submit
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
                except:
                    continue

            if submit_button:
                logger.info("Enviando login...")
                submit_button.click()
            else:
                # Fallback: presionar Enter
                password_field.press('Enter')

            # Esperar autenticación
            logger.info("Esperando autenticación...")
            time.sleep(5)

            # Verificar si estamos en IEEE
            current_url = self._page.url
            if "ieeexplore.ieee.org" in current_url or "IEEE" in self._page.title():
                logger.info("✓ Autenticación exitosa")
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
                'source': 'IEEE Xplore'
            }
        """
        try:
            # Iniciar navegador si no está activo
            if not self._page:
                self._start_browser()

            # Autenticar si no lo está
            if not self._authenticated:
                self._authenticate()

            logger.info(f"Buscando: '{query}' (max: {max_results})")

            # Primero navegar a IEEE para establecer contexto
            search_url = f"{self.IEEE_SEARCH_URL}?queryText={query}"
            logger.info(f"Navegando a: {search_url}")
            self._page.goto(search_url, wait_until='load', timeout=self.timeout * 2)
            time.sleep(2)

            # Intentar llamar directamente al API usando page.request
            logger.info("Llamando a /rest/search API...")
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
                    logger.info(f"✓ API: {len(records)} resultados (total: {data.get('totalRecords', 0)})")

                    for i, record in enumerate(records):
                        if i >= max_results:
                            break
                        yield self._normalize_record(record)

                    logger.info(f"✓ Retornados {min(len(records), max_results)} resultados")
                else:
                    logger.warning(f"API falló: {response.status}")
                    raise Exception(f"API error: {response.status}")

            except Exception as api_error:
                logger.warning(f"API directa falló: {api_error}")
                logger.warning("Intentando scraping HTML como fallback...")

                # Fallback: scraping HTML
                yield from self._scrape_html_results(max_results)

            # Rate limiting
            time.sleep(self.rate_limit)

        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            raise

    def _normalize_record(self, record: Dict) -> Dict[str, Any]:
        """Normaliza un registro de /rest/search al contrato esperado"""
        article_number = record.get('articleNumber', '')
        is_open_access, pdf_url = self._extract_access_info(record, article_number)

        # Extraer autores
        authors = []
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
        """Fallback: scraping HTML si /rest/search falla"""
        logger.info("Scraping HTML...")

        # Esperar a que carguen los resultados
        time.sleep(3)

        # Buscar resultados en la página - múltiples selectores
        result_containers = self._page.query_selector_all('.List-results-items')

        if not result_containers:
            # Intentar selector alternativo
            result_containers = self._page.query_selector_all('[class*="result-item"]')

        if not result_containers:
            # Otro selector
            result_containers = self._page.query_selector_all('.result-item-align')

        count = 0
        for container in result_containers:
            if count >= max_results:
                break

            try:
                # Título
                title_elem = container.query_selector('a.fw-bold, h2 a, h3 a, .result-item-title a')
                title = title_elem.inner_text().strip() if title_elem else 'N/A'

                # Link
                link = ''
                if title_elem:
                    href = title_elem.get_attribute('href')
                    if href:
                        if href.startswith('/'):
                            link = 'https://ieeexplore.ieee.org' + href
                        else:
                            link = href

                # Article number (para reconstruir URLs)
                article_number = ''
                if link:
                    match = re.search(r'/document/(\\d+)', link)
                    if match:
                        article_number = match.group(1)

                # DOI - buscar en múltiples lugares
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
                            # Extraer DOI del texto
                            doi_match = re.search(r'10\.\d{4,}/[^\s]+', doi_text)
                            if doi_match:
                                doi = doi_match.group(0)
                                break
                    except:
                        continue

                # Autores
                authors = []
                authors_elem = container.query_selector('.author, [class*="authors"]')
                if authors_elem:
                    authors_text = authors_elem.inner_text().strip()
                    # Separar por ; o ,
                    if ';' in authors_text:
                        authors = [a.strip() for a in authors_text.split(';') if a.strip()]
                    elif ',' in authors_text:
                        authors = [a.strip() for a in authors_text.split(',') if a.strip()]
                    else:
                        authors = [authors_text] if authors_text else []

                # Año
                year = None
                year_elem = container.query_selector('[class*="year"], [class*="date"]')
                if year_elem:
                    year_text = year_elem.inner_text().strip()
                    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', year_text)
                    if year_match:
                        year = int(year_match.group(1))

                # Abstract (generalmente no está en la lista, pero intentamos)
                abstract = None
                abstract_elem = container.query_selector('[class*="abstract"], [class*="snippet"]')
                if abstract_elem:
                    abstract = abstract_elem.inner_text().strip()

                # Open Access flag (icono en el listado)
                is_open_access = None
                access_elem = container.query_selector('.xpl-access-type-icon, [class*="access-type" i], [class*="open-access" i]')
                if access_elem:
                    access_text = (access_elem.inner_text() or "").lower()
                    access_attr = (access_elem.get_attribute('title') or "").lower()
                    combined = f"{access_text} {access_attr}"
                    if 'open' in combined:
                        is_open_access = True
                    elif 'denied' in combined or 'closed' in combined or 'subscription' in combined:
                        is_open_access = False

                # URL directa al PDF si está visible en el listado
                pdf_url = None
                pdf_elem = container.query_selector('a[href*="stamp/stamp.jsp"], a[title*="PDF" i], a.icon-pdf, a[href*="/pdf/"]')
                if pdf_elem:
                    href = pdf_elem.get_attribute('href')
                    if href:
                        if href.startswith('/'):
                            pdf_url = 'https://ieeexplore.ieee.org' + href
                        else:
                            pdf_url = href

                if not pdf_url and article_number and is_open_access:
                    pdf_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={article_number}"

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
                logger.warning(f"Error scraping resultado: {e}")
                continue

        logger.info(f"✓ HTML scraping: {count} resultados")

    def close(self):
        """Cierra el navegador y libera recursos"""
        self._stop_browser()

    def __enter__(self):
        """Context manager support"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support"""
        self.close()

    def _extract_access_info(self, record: Dict[str, Any], article_number: str) -> tuple[Optional[bool], Optional[str]]:
        """Inferir OA y URL del PDF desde el registro devuelto por /rest/search."""
        is_open_access: Optional[bool] = None
        for field in ["openAccessFlag", "isOa", "openAccess", "isOpenAccess"]:
            if field in record:
                value = record.get(field)
                if isinstance(value, str):
                    normalized = value.lower()
                    if "open" in normalized:
                        is_open_access = True
                    elif "denied" in normalized or "closed" in normalized or "subscription" in normalized:
                        is_open_access = False
                else:
                    is_open_access = bool(value) if value is not None else None
                if is_open_access is not None:
                    break

        access_type = record.get("accessType") or record.get("accessType_s") or record.get("accessTypeIcon") or record.get("accessType_x")
        if is_open_access is None and isinstance(access_type, str):
            normalized = access_type.lower()
            if "open" in normalized:
                is_open_access = True
            elif "denied" in normalized or "closed" in normalized or "subscription" in normalized:
                is_open_access = False

        pdf_url = record.get("pdfLink") or record.get("htmlLink") or record.get("fullTextLink")
        if isinstance(pdf_url, list):
            pdf_url = pdf_url[0] if pdf_url else None

        if pdf_url and isinstance(pdf_url, str) and pdf_url.startswith('/'):
            pdf_url = f"https://ieeexplore.ieee.org{pdf_url}"

        if not pdf_url and article_number and is_open_access:
            pdf_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={article_number}"

        return is_open_access, pdf_url
