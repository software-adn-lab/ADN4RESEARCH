"""
Session Manager específico para Scopus vía EZproxy.
"""
import logging
import time
from playwright.sync_api import Page, BrowserContext
import requests

from .session_manager import SessionManager

logger = logging.getLogger(__name__)


class ScopusSessionManager(SessionManager):
    """Maneja sesión persistente de Scopus vía EZproxy EPN"""

    # URLs - SIEMPRE a través de EZproxy (puerto 2057)
    SCOPUS_VIA_EZPROXY = "https://bvirtual.epn.edu.ec/login?url=http://www.scopus.com"
    SCOPUS_PROXY_HOME = "https://bvirtual.epn.edu.ec:2057/pages/home?display=basic#basic"
    # TODO: Descubrir endpoint de búsqueda de Scopus
    # SCOPUS_PROXY_SEARCH = "https://bvirtual.epn.edu.ec:2057/[ENDPOINT_A_DESCUBRIR]"

    def __init__(self, username: str, password: str, headless: bool = True):
        super().__init__(
            username=username,
            password=password,
            session_file=".sessions/scopus_session.json",
            headless=headless,
            timeout=30000
        )

    def _perform_login(self, page: Page, context: BrowserContext) -> bool:
        """Realiza login en EZproxy para Scopus"""
        try:
            logger.info(f"Navegando a Scopus vía EZproxy...")
            page.goto(self.SCOPUS_VIA_EZPROXY, wait_until='networkidle', timeout=self.timeout)

            time.sleep(2)

            current_url = page.url

            # Si ya estamos en Scopus, sesión activa
            if "scopus.com" in current_url:
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
            if "scopus.com" in current_url or "Scopus" in page.title():
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

        Intenta acceder a Scopus via EZproxy con las cookies.
        Si estás FUERA de la red y las cookies son válidas → 200
        """
        return self.session.get(
            self.SCOPUS_PROXY_HOME,
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
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })

        # Request de prueba VIA EZPROXY
        # Si la IP está autorizada, responderá 200
        return temp_session.get(
            self.SCOPUS_PROXY_HOME,  # SIEMPRE a través de EZproxy
            timeout=10,
            allow_redirects=False  # Si redirige (302) = no estás en la red
        )
