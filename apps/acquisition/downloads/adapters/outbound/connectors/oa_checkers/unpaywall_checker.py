"""
UnpaywallChecker - Verifica OA usando Unpaywall API (primer eslabón de la cadena).

Patrón: Chain of Responsibility
- Hereda de BaseOpenAccessChecker
- Si no encuentra OA, pasa al siguiente checker de la cadena

API: https://unpaywall.org/products/api
"""

import requests
import logging
from typing import Optional, Dict

from apps.acquisition.downloads.domain.interfaces import (
    BaseOpenAccessChecker,
    OpenAccessResult,
)
from apps.acquisition.shared.domain.value_objects.doi import DOI

logger = logging.getLogger(__name__)


class UnpaywallChecker(BaseOpenAccessChecker):
    """
    Checker de Open Access vía Unpaywall API.

    Implementa el patrón Chain of Responsibility: si no encuentra OA,
    pasa la responsabilidad al siguiente checker de la cadena.

    Uso:
        # Como primer eslabón de la cadena
        crossref = CrossrefChecker(email="...", next_checker=scopus)
        checker = UnpaywallChecker(email="researcher@epn.edu.ec", next_checker=crossref)
        result = checker.check_access(doi)
        
        # Uso simple (sin cadena)
        checker = UnpaywallChecker(email="researcher@epn.edu.ec")
        result = checker.check_access(doi)
    """

    BASE_URL = "https://api.unpaywall.org/v2"

    def __init__(
        self,
        email: str,
        timeout: float = 5.0,
        next_checker: Optional[BaseOpenAccessChecker] = None,
    ):
        """
        Inicializar el checker de Unpaywall.

        Args:
            email: Email de contacto (requerido por Unpaywall API)
            timeout: Timeout en segundos para las peticiones HTTP
            next_checker: Siguiente checker de la cadena (Chain of Responsibility)

        Raises:
            ValueError: Si no se proporciona email
        """
        super().__init__(next_checker)
        
        if not email:
            raise ValueError("Se requiere un email para usar la API de Unpaywall")

        self.email = email
        self.timeout = timeout
        self._cache: Dict[str, OpenAccessResult] = {}

    @property
    def source_name(self) -> str:
        """Nombre de la fuente para logging y resultados."""
        return "Unpaywall"

    def check_access(self, doi: DOI) -> OpenAccessResult:
        """
        Verificar Open Access en Unpaywall.
        
        Si encuentra OA, retorna el resultado.
        Si no encuentra, pasa al siguiente checker de la cadena.

        Args:
            doi: DOI del estudio a verificar

        Returns:
            OpenAccessResult con información del acceso
        """
        # Validación básica
        if not doi or not doi.value:
            logger.warning("DOI vacío o None, no se puede verificar OA")
            return self._pass_to_next(doi)

        # Revisar cache
        if doi.value in self._cache:
            cached = self._cache[doi.value]
            logger.debug(f"OA status obtenido de cache: {doi.value}")
            if cached.is_oa:
                return cached
            # Si no era OA en cache, intentar con el siguiente
            return self._pass_to_next(doi)

        # Consultar API
        try:
            url = f"{self.BASE_URL}/{doi.value}"
            params = {"email": self.email}

            logger.debug(f"Consultando Unpaywall: {doi.value}")
            response = requests.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                is_oa = bool(data.get("is_oa", False))
                
                if is_oa:
                    best_loc = data.get("best_oa_location", {}) or {}
                    result = OpenAccessResult(
                        is_oa=True,
                        pdf_url=best_loc.get("url_for_pdf"),
                        landing_url=best_loc.get("url_for_landing_page"),
                        source=self.source_name,
                        version=best_loc.get("version"),
                        license=best_loc.get("license"),
                    )
                    self._cache[doi.value] = result
                    logger.info(f"✅ Open Access encontrado en Unpaywall: {doi.value}")
                    return result
                else:
                    # No es OA, cachear y pasar al siguiente
                    not_found = OpenAccessResult.not_found(source=self.source_name)
                    self._cache[doi.value] = not_found
                    logger.debug(f"🔒 Paywall detectado en Unpaywall: {doi.value}")
                    return self._pass_to_next(doi)

            elif response.status_code == 404:
                logger.warning(f"DOI no encontrado en Unpaywall: {doi.value}")
                self._cache[doi.value] = OpenAccessResult.not_found(source=self.source_name)
                return self._pass_to_next(doi)

            else:
                logger.error(f"Unpaywall HTTP {response.status_code}: {doi.value}")
                return self._pass_to_next(doi)

        except requests.Timeout:
            logger.error(f"Timeout al consultar Unpaywall: {doi.value}")
            return self._pass_to_next(doi)

        except requests.RequestException as e:
            logger.error(f"Error de red con Unpaywall para {doi.value}: {e}")
            return self._pass_to_next(doi)

        except Exception as e:
            logger.error(f"Error inesperado en Unpaywall para {doi.value}: {e}")
            return self._pass_to_next(doi)

    def clear_cache(self) -> None:
        """Limpiar el cache de resultados OA."""
        self._cache.clear()
        logger.debug("Cache de Unpaywall limpiado")
