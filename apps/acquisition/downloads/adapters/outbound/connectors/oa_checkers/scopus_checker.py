"""
ScopusChecker - Verifica OA usando Scopus/Elsevier API (último eslabón de la cadena).

Se usa como último recurso legal para estudios de Scopus cuando Unpaywall/Crossref
no encontraron OA, aprovechando la suscripción institucional si existe.

Patrón: Chain of Responsibility
- Hereda de BaseOpenAccessChecker
- Típicamente es el último eslabón de la cadena (next_checker=None)
"""

import logging
from typing import Optional

import requests

from apps.acquisition.downloads.domain.interfaces import (
    BaseOpenAccessChecker,
    OpenAccessResult,
)
from apps.acquisition.shared.domain.value_objects.doi import DOI

logger = logging.getLogger(__name__)


class ScopusChecker(BaseOpenAccessChecker):
    """
    Checker de Open Access usando la API de Scopus (Elsevier).

    Implementa el patrón Chain of Responsibility: normalmente es el último
    eslabón de la cadena de checkers legales.

    Estrategia:
    - Consulta abstract por DOI con apiKey institucional
    - Evalúa flag de open access si está disponible
    - Retorna landing_url hacia el publisher cuando no hay PDF directo
    """

    BASE_URL = "https://api.elsevier.com/content/abstract/doi"

    def __init__(
        self,
        api_key: str,
        timeout: float = 10.0,
        next_checker: Optional[BaseOpenAccessChecker] = None,
    ):
        """
        Inicializar el checker de Scopus.

        Args:
            api_key: API Key de Scopus/Elsevier
            timeout: Timeout en segundos para las peticiones HTTP
            next_checker: Siguiente checker de la cadena (normalmente None)

        Raises:
            ValueError: Si no se proporciona api_key
        """
        super().__init__(next_checker)
        
        if not api_key:
            raise ValueError("Se requiere SCOPUS_API_KEY para ScopusChecker")
        
        self.api_key = api_key
        self.timeout = timeout

    @property
    def source_name(self) -> str:
        """Nombre de la fuente para logging y resultados."""
        return "Scopus"

    def check_access(self, doi: DOI) -> OpenAccessResult:
        """
        Verificar Open Access en Scopus.

        Si encuentra OA, retorna el resultado.
        Si no encuentra, pasa al siguiente checker de la cadena.

        Args:
            doi: DOI del estudio a verificar

        Returns:
            OpenAccessResult con información del acceso
        """
        if not doi or not doi.value:
            return self._pass_to_next(doi)

        try:
            url = f"{self.BASE_URL}/{doi.value}"
            headers = {
                "X-ELS-APIKey": self.api_key,
                "Accept": "application/json",
            }
            resp = requests.get(url, headers=headers, timeout=self.timeout)
            
            if resp.status_code != 200:
                logger.debug(f"Scopus OA HTTP {resp.status_code} para {doi.value}")
                return self._pass_to_next(doi)

            data = resp.json()
            # Estructura típica: abstracts-retrieval-response/coredata
            core = (
                data.get("abstracts-retrieval-response", {}).get("coredata", {})
                if isinstance(data, dict)
                else {}
            )

            # Campo openaccess suele ser "1" o "0" (string)
            oa_flag = core.get("openaccess")
            is_oa = str(oa_flag) == "1"
            oa_type = core.get("openaccessType") or None

            # Links disponibles
            links = core.get("link", []) or []
            landing_url = None
            pdf_url = None

            for link in links:
                rel = (link.get("@rel") or "").lower()
                href = link.get("@href")
                if not href:
                    continue

                # Prioridad 1: enlaces explícitos de texto completo
                if rel in {"full-text", "scopus-ft", "scopus-full-text"} and not pdf_url:
                    pdf_url = href
                    if not landing_url:
                        landing_url = href
                    continue

                # Prioridad 2: landing institucional (visor)
                if rel in {"scidir", "scopus"} and not landing_url:
                    landing_url = href
                    continue

                # Prioridad 3: DOI como fallback de landing
                if rel == "doi" and not landing_url:
                    landing_url = href

            if is_oa:
                result = OpenAccessResult(
                    is_oa=True,
                    pdf_url=pdf_url,
                    landing_url=landing_url,
                    source=self.source_name,
                    oa_type=oa_type,
                )
                logger.info(f"✅ Open Access encontrado en Scopus: {doi.value}")
                return result

            logger.debug(f"🔒 No OA en Scopus: {doi.value}")
            return self._pass_to_next(doi)

        except requests.Timeout:
            logger.error(f"Timeout al consultar Scopus: {doi.value}")
            return self._pass_to_next(doi)

        except requests.RequestException as e:
            logger.error(f"Error de red con Scopus para {doi.value}: {e}")
            return self._pass_to_next(doi)

        except Exception as exc:
            logger.warning(f"Error consultando Scopus OA para {doi.value}: {exc}")
            return self._pass_to_next(doi)


# Alias para backward compatibility
ScopusInstitutionalChecker = ScopusChecker
