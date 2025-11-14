"""
Session Manager específico para IEEE Xplore vía EZproxy.
"""
import logging
import time
from playwright.sync_api import Page, BrowserContext
import requests

from .session_manager import SessionManager

logger = logging.getLogger(__name__)


class IeeeSessionManager(SessionManager):
    """Maneja sesión persistente de IEEE Xplore vía EZproxy EPN"""

    # URLs - SIEMPRE a través de EZproxy (puerto 2097)
    IEEE_VIA_EZPROXY = "https://bvirtual.epn.edu.ec/login?url=http://ieeexplore.ieee.org/Xplore/home.jsp"
    IEEE_PROXY_HOME = "https://bvirtual.epn.edu.ec:2097/Xplore/home.jsp"
    IEEE_PROXY_SEARCH = "https://bvirtual.epn.edu.ec:2097/rest/search"

    def __init__(self, username: str, password: str, headless: bool = True):
        super().__init__(
            username=username,
            password=password,
            session_file=".sessions/ieee_session.json",
            headless=headless,
            timeout=30000
        )

    def _perform_login(self, page: Page, context: BrowserContext) -> bool:
        """Realiza login en EZproxy para IEEE"""
        try:
            logger.info(f"Navegando a IEEE vía EZproxy...")
            page.goto(self.IEEE_VIA_EZPROXY, wait_until='networkidle', timeout=self.timeout)

            time.sleep(2)

            current_url = page.url

            # Si ya estamos en IEEE, sesión activa
            if "ieeexplore.ieee.org" in current_url:
                logger.info("✓ Sesión activa detectada")
                return True

            # Buscar formulario de login
            logger.info("Buscando formulario de login...")

            username_field = None
            username_selectors = [
                'input[name="user"]',
                'input[name="username"]',
                'input[name="email"]',
                'input[type="email"]',
                'input[id="username"]'
            ]

            for selector in username_selectors:
                try:
                    username_field = page.query_selector(selector)
                    if username_field:
                        logger.info(f"✓ Campo usuario: {selector}")
                        break
                except:
                    continue

            password_field = page.query_selector('input[type="password"]')

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
                    submit_button = page.query_selector(selector)
                    if submit_button:
                        break
                except:
                    continue

            if submit_button:
                logger.info("Clickeando submit...")
                submit_button.click()
            else:
                logger.info("Presionando Enter...")
                password_field.press('Enter')

            # Esperar autenticación
            logger.info("Esperando autenticación...")
            time.sleep(5)

            # Verificar éxito
            current_url = page.url
            if "ieeexplore.ieee.org" in current_url or "IEEE" in page.title():
                logger.info("✓ Login exitoso")
                return True
            else:
                logger.error(f"Login falló. URL: {current_url}")
                return False

        except Exception as e:
            logger.error(f"Error en login: {e}")
            return False

    def _test_session(self) -> requests.Response:
        """
        Prueba sesión con cookies guardadas.

        Intenta acceder al endpoint de búsqueda de EZproxy con las cookies.
        Si estás FUERA de la red y las cookies son válidas → 200
        """
        payload = {
            "queryText": "test",
            "rowsPerPage": 1,
            "pageNumber": 1
        }

        return self.session.post(
            self.IEEE_PROXY_SEARCH,
            json=payload,
            timeout=10,
            allow_redirects=False
        )

    def _test_direct_access(self) -> requests.Response:
        """
        Prueba acceso directo por IP (sin cookies) al EZproxy.

        Si estás EN LA RED universitaria, el EZproxy detecta tu IP
        y te deja pasar sin autenticación → 200

        Si estás FUERA, te redirige al login → 302
        """
        # Crear sesión temporal SIN cookies
        temp_session = requests.Session()
        temp_session.headers.update({
            'User-Agent': self.USER_AGENT,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })

        # Request de prueba al endpoint de búsqueda VIA EZPROXY
        payload = {
            "queryText": "test",
            "rowsPerPage": 1,
            "pageNumber": 1
        }

        return temp_session.post(
            self.IEEE_PROXY_SEARCH,  # SIEMPRE a través de EZproxy
            json=payload,
            timeout=10,
            allow_redirects=False  # Si redirige (302) = no estás en la red
        )
