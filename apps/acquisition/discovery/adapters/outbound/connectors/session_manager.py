"""
Session Manager para mantener sesiones persistentes con EZproxy.

Patrón:
1. Primera vez: Playwright → Login → Guardar cookies
2. Siguientes veces: Reutilizar cookies (sin navegador)
3. Si cookies expiran: Re-autenticar automáticamente
"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
import requests
from playwright.sync_api import sync_playwright, Page, BrowserContext
import time

logger = logging.getLogger(__name__)


class SessionManager(ABC):
    """
    Clase base para manejar sesiones persistentes.

    Responsabilidades:
    - Verificar si hay sesión válida
    - Autenticar cuando sea necesario
    - Guardar/cargar cookies
    - Proveer sesión de requests lista para usar
    """

    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    def __init__(
        self,
        username: str,
        password: str,
        session_file: str,
        headless: bool = True,
        timeout: int = 30000
    ):
        """
        Args:
            username: Usuario institucional
            password: Contraseña institucional
            session_file: Archivo donde guardar cookies
            headless: Ejecutar navegador sin GUI
            timeout: Timeout en ms para operaciones Playwright
        """
        self.username = username
        self.password = password
        self.session_file = Path(session_file)
        self.headless = headless
        self.timeout = timeout

        # Sesión de requests con User-Agent consistente
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

        # Cargar cookies si existen
        self._load_cookies()

    def ensure_authenticated(self) -> bool:
        """
        Asegura que hay sesión válida.

        Estrategia:
        1. Intentar acceso directo por IP (si estás en red universitaria)
        2. Si falla, intentar con cookies guardadas
        3. Si falla, autenticar con Playwright

        Returns:
            True si hay sesión válida (IP, cookies o recién autenticada)
        """
        logger.info("🔍 Verificando acceso directo por IP (red universitaria)...")
        if self._has_direct_access():
            logger.info("✅ Acceso directo por IP detectado (estás en la red universitaria)")
            logger.info("   No se requiere autenticación ni cookies")
            return True

        logger.info("⚠️  Sin acceso directo. Verificando cookies guardadas...")
        if self._has_valid_session():
            logger.info("✓ Sesión válida con cookies detectada")
            return True

        logger.info("⚠️  No hay sesión válida, autenticando con Playwright...")
        return self._authenticate()

    def _has_direct_access(self) -> bool:
        """
        Verifica si hay acceso directo por IP (red universitaria).

        Returns:
            True si se puede acceder sin cookies (IP autorizada)
        """
        try:
            response = self._test_direct_access()

            if response.status_code == 200:
                logger.info("   ✓ Request de prueba exitoso sin cookies")
                self.session.cookies.clear()
                logger.debug("   Cookies limpiadas (no necesarias con acceso por IP)")
                return True
            else:
                logger.debug(f"   Request directo falló: {response.status_code}")
                return False

        except Exception as e:
            logger.debug(f"   Sin acceso directo: {e}")
            return False

    def _has_valid_session(self) -> bool:
        """
        Verifica si las cookies cargadas son válidas.

        Returns:
            True si la sesión es válida
        """
        if not self.session.cookies:
            return False

        try:
            response = self._test_session()
            return response.status_code == 200
        except:
            return False

    def _load_cookies(self) -> bool:
        """Carga cookies desde archivo"""
        if not self.session_file.exists():
            logger.debug(f"No existe archivo de sesión: {self.session_file}")
            return False

        try:
            with open(self.session_file, 'r') as f:
                cookies_data = json.load(f)

            for cookie in cookies_data:
                self.session.cookies.set(
                    cookie['name'],
                    cookie['value'],
                    domain=cookie.get('domain'),
                    path=cookie.get('path', '/')
                )

            logger.info(f"✓ Cookies cargadas: {len(cookies_data)} items")
            return True

        except Exception as e:
            logger.warning(f"Error cargando cookies: {e}")
            return False

    def _save_cookies(self, cookies_list: list):
        """Guarda cookies a archivo"""
        try:
            self.session_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.session_file, 'w') as f:
                json.dump(cookies_list, f, indent=2)

            logger.info(f"✓ Cookies guardadas: {len(cookies_list)} items")

        except Exception as e:
            logger.error(f"Error guardando cookies: {e}")

    def _authenticate(self) -> bool:
        """
        Autentica usando Playwright.

        Returns:
            True si autenticación exitosa
        """
        logger.info("🔐 Autenticando con Playwright...")

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)

                context = browser.new_context(
                    user_agent=self.USER_AGENT,
                    viewport={'width': 1920, 'height': 1080},
                    locale='en-US',
                    timezone_id='America/Guayaquil'
                )
                page = context.new_page()

                success = self._perform_login(page, context)

                if success:
                    cookies_list = context.cookies()
                    self._save_cookies(cookies_list)

                    for cookie in cookies_list:
                        self.session.cookies.set(
                            cookie['name'],
                            cookie['value'],
                            domain=cookie.get('domain'),
                            path=cookie.get('path', '/')
                        )

                    logger.info("✅ Autenticación exitosa")

                browser.close()
                return success

        except Exception as e:
            logger.error(f"❌ Error en autenticación: {e}")
            return False

    @abstractmethod
    def _perform_login(self, page: Page, context: BrowserContext) -> bool:
        """
        Realiza el login en la página.

        Debe ser implementado por cada conector específico.

        Args:
            page: Página de Playwright
            context: Contexto del navegador

        Returns:
            True si login exitoso
        """
        pass

    @abstractmethod
    def _test_session(self) -> requests.Response:
        """
        Hace request de prueba para verificar si sesión es válida.

        Returns:
            Response del request de prueba
        """
        pass

    @abstractmethod
    def _test_direct_access(self) -> requests.Response:
        """
        Hace request de prueba SIN cookies para verificar acceso directo por IP.

        Returns:
            Response del request de prueba
        """
        pass
