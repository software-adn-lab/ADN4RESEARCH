"""
UnpaywallChecker - Implementación REAL de IOpenAccessChecker usando Unpaywall API.

Este conector consulta la API de Unpaywall para determinar si un estudio
es Open Access y obtener la URL del PDF.

API: https://unpaywall.org/products/api
"""

import requests
import logging
from typing import Optional, Dict, Any

from apps.acquisition.shared.domain.value_objects.doi import DOI

logger = logging.getLogger(__name__)


class UnpaywallChecker:
    """
    Implementación REAL del contrato IOpenAccessChecker.

    Consulta la API gratuita de Unpaywall para determinar Open Access.

    Uso:
        checker = UnpaywallChecker(email="researcher@epn.edu.ec")
        is_oa = checker.is_open_access(doi)
    """

    BASE_URL = "https://api.unpaywall.org/v2"

    def __init__(self, email: str, timeout: float = 5.0):
        """
        Inicializar el checker de Unpaywall.

        Args:
            email: Email de contacto (requerido por Unpaywall API)
            timeout: Timeout en segundos para las peticiones HTTP

        Raises:
            ValueError: Si no se proporciona email
        """
        if not email:
            raise ValueError("Se requiere un email para usar la API de Unpaywall")

        self.email = email
        self.timeout = timeout
        self._cache: Dict[str, bool] = {}  # Cache simple para evitar llamadas repetidas

    def is_open_access(self, doi: DOI) -> bool:
        """
        Implementación del contrato IOpenAccessChecker.

        Consulta Unpaywall para determinar si un DOI es Open Access.

        Args:
            doi: DOI del estudio a verificar

        Returns:
            True si es Open Access, False en caso contrario

        Ejemplos:
            >>> checker = UnpaywallChecker("test@epn.edu.ec")
            >>> checker.is_open_access(DOI("10.1371/journal.pone.0000308"))
            True
            >>> checker.is_open_access(DOI("10.1038/nature12373"))
            False
        """
        # Validación básica
        if not doi or not doi.value:
            logger.warning("DOI vacío o None, no se puede verificar OA")
            return False

        # Revisar cache
        if doi.value in self._cache:
            logger.debug(f"OA status obtenido de cache: {doi.value}")
            return self._cache[doi.value]

        # Consultar API
        try:
            url = f"{self.BASE_URL}/{doi.value}"
            params = {"email": self.email}

            logger.debug(f"Consultando Unpaywall: {doi.value}")
            response = requests.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                is_oa = bool(data.get('is_oa', False))

                # Cachear resultado
                self._cache[doi.value] = is_oa

                if is_oa:
                    logger.info(f"✅ Open Access encontrado: {doi.value}")
                else:
                    logger.debug(f"🔒 Paywall detectado: {doi.value}")

                return is_oa

            elif response.status_code == 404:
                logger.warning(f"DOI no encontrado en Unpaywall: {doi.value}")
                self._cache[doi.value] = False
                return False

            else:
                logger.error(f"Unpaywall HTTP {response.status_code}: {doi.value}")
                return False

        except requests.Timeout:
            logger.error(f"Timeout al consultar Unpaywall: {doi.value}")
            return False

        except requests.RequestException as e:
            logger.error(f"Error de red con Unpaywall para {doi.value}: {e}")
            return False

        except Exception as e:
            logger.error(f"Error inesperado en Unpaywall para {doi.value}: {e}")
            return False

    def get_oa_info(self, doi: DOI) -> Optional[Dict[str, Any]]:
        """
        Método auxiliar para obtener información completa de OA (no es parte del contrato).

        Útil para casos donde necesitamos más detalles (URL, versión, licencia).

        Args:
            doi: DOI del estudio

        Returns:
            Diccionario con información OA o None si falla

        Ejemplo de respuesta:
            {
                "is_oa": True,
                "pdf_url": "https://...",
                "version": "publishedVersion",
                "license": "cc-by",
                "host_type": "publisher"
            }
        """
        if not doi or not doi.value:
            return None

        try:
            url = f"{self.BASE_URL}/{doi.value}"
            params = {"email": self.email}

            response = requests.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                best_loc = data.get('best_oa_location', {}) or {}

                return {
                    "is_oa": bool(data.get('is_oa', False)),
                    "pdf_url": best_loc.get('url_for_pdf'),
                    "landing_url": best_loc.get('url_for_landing_page'),
                    "version": best_loc.get('version'),
                    "license": best_loc.get('license'),
                    "host_type": best_loc.get('host_type'),
                }

            return None

        except Exception as e:
            logger.error(f"Error obteniendo info OA completa para {doi.value}: {e}")
            return None

    def clear_cache(self):
        """Limpiar el cache de resultados OA."""
        self._cache.clear()
        logger.debug("Cache de Unpaywall limpiado")
