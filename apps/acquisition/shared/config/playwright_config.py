"""
Configuración centralizada de Playwright para todos los conectores.

Este módulo unifica la configuración de Playwright en toda la aplicación,
evitando inconsistencias y facilitando cambios globales.

Uso:
    from apps.acquisition.shared.config.playwright_config import get_playwright_config

    cfg = get_playwright_config()
    browser = playwright.chromium.launch(headless=cfg.headless)
"""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PlaywrightConfig:
    """
    Configuración inmutable para Playwright.

    Attributes:
        headless: Si el navegador debe ejecutarse sin interfaz gráfica
        timeout_ms: Timeout en milisegundos para operaciones del navegador
        viewport_width: Ancho del viewport cuando no es headless
        viewport_height: Alto del viewport cuando no es headless
    """
    headless: bool
    timeout_ms: int
    viewport_width: int
    viewport_height: int

    @classmethod
    def from_env(cls) -> "PlaywrightConfig":
        """
        Cargar configuración desde variables de entorno.

        Variables de entorno soportadas:
            HEADLESS_MODE: "true", "false", "1", "0" (default: "true")
            BROWSER_TIMEOUT: Timeout en milisegundos (default: "30000")
            BROWSER_WIDTH: Ancho del viewport (default: "1280")
            BROWSER_HEIGHT: Alto del viewport (default: "720")

        Returns:
            PlaywrightConfig con valores del .env o defaults
        """
        headless_str = os.getenv("HEADLESS_MODE", "true").strip().lower()
        headless = headless_str in ("1", "true", "yes", "y")

        timeout_ms = int(os.getenv("BROWSER_TIMEOUT", "30000"))
        width = int(os.getenv("BROWSER_WIDTH", "1280"))
        height = int(os.getenv("BROWSER_HEIGHT", "720"))

        return cls(
            headless=headless,
            timeout_ms=timeout_ms,
            viewport_width=width,
            viewport_height=height,
        )


def get_playwright_config() -> PlaywrightConfig:
    """
    Helper sencillo para obtener la configuración actual.

    Returns:
        PlaywrightConfig cargado desde variables de entorno
    """
    return PlaywrightConfig.from_env()


def get_viewport_dict(headless: bool) -> dict | None:
    """
    Obtener configuración de viewport basado en modo headless.

    Args:
        headless: Si el navegador está en modo headless

    Returns:
        Dict con configuración de viewport o None para modo no-headless
    """
    if headless:
        cfg = get_playwright_config()
        return {
            'width': cfg.viewport_width,
            'height': cfg.viewport_height,
        }
    return None


def get_browser_args(headless: bool) -> list[str]:
    """
    Obtener argumentos para el lanzamiento del navegador.

    Args:
        headless: Si el navegador está en modo headless

    Returns:
        Lista de argumentos para browser.launch()
    """
    if headless:
        return []
    else:
        return ['--start-maximized']