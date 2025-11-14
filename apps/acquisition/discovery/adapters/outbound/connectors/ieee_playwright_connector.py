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

            # Variable para capturar respuesta de /rest/search
            captured_response = None

            def handle_response(response):
                nonlocal captured_response
                if '/rest/search' in response.url and response.request.method == 'POST':
                    try:
                        captured_response = response.json()
                        logger.info(f"✓ Capturado /rest/search: {len(captured_response.get('records', []))} resultados")
                    except:
                        pass

            # Registrar listener para capturar respuestas
            self._page.on('response', handle_response)

            # Navegar a búsqueda
            search_url = f"{self.IEEE_SEARCH_URL}?queryText={query}"
            logger.info(f"Navegando a: {search_url}")

            self._page.goto(search_url, wait_until='networkidle', timeout=self.timeout)

            # Esperar a que se capture la respuesta
            time.sleep(3)

            # Quitar listener
            self._page.remove_listener('response', handle_response)

            # Procesar resultados
            if captured_response and 'records' in captured_response:
                records = captured_response['records']
                logger.info(f"Procesando {len(records)} resultados...")

                for i, record in enumerate(records):
                    if i >= max_results:
                        break

                    yield self._normalize_record(record)

                logger.info(f"✓ Retornados {min(len(records), max_results)} resultados")
            else:
                logger.warning("No se capturaron resultados de /rest/search")
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

        return {
            'title': record.get('articleTitle', 'N/A'),
            'link': f"https://ieeexplore.ieee.org/document/{article_number}" if article_number else '',
            'doi': record.get('doi'),
            'source': 'IEEE Xplore'
        }

    def _scrape_html_results(self, max_results: int) -> Iterable[Dict[str, Any]]:
        """Fallback: scraping HTML si /rest/search falla"""
        logger.info("Scraping HTML...")

        # Buscar resultados en la página
        result_containers = self._page.query_selector_all('.List-results-items')

        count = 0
        for container in result_containers:
            if count >= max_results:
                break

            try:
                title_elem = container.query_selector('a.fw-bold')
                title = title_elem.inner_text() if title_elem else 'N/A'

                link_elem = container.query_selector('a.fw-bold')
                link = 'https://ieeexplore.ieee.org' + link_elem.get_attribute('href') if link_elem else ''

                doi_elem = container.query_selector('.col :text("DOI:")')
                doi = doi_elem.inner_text().replace('DOI:', '').strip() if doi_elem else None

                yield {
                    'title': title,
                    'link': link,
                    'doi': doi,
                    'source': 'IEEE Xplore'
                }

                count += 1
            except Exception as e:
                logger.warning(f"Error scraping resultado: {e}")
                continue

        logger.info(f"✓ HTML: {count} resultados")

    def close(self):
        """Cierra el navegador y libera recursos"""
        self._stop_browser()

    def __enter__(self):
        """Context manager support"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support"""
        self.close()
