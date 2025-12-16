"""
CrossrefChecker - Verifica OA usando Crossref API (segundo eslabón de la cadena).

Este checker actúa como respaldo cuando Unpaywall no encuentra OA. Busca enlaces en el
campo `link` de la respuesta de Crossref con content-type PDF, y también señales de licencia
que indiquen acceso abierto.

Patrón: Chain of Responsibility
- Hereda de BaseOpenAccessChecker
- Si no encuentra OA, pasa al siguiente checker de la cadena
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


class CrossrefChecker(BaseOpenAccessChecker):
    """
    Checker de Open Access vía Crossref API.

    Implementa el patrón Chain of Responsibility: si no encuentra OA,
    pasa la responsabilidad al siguiente checker de la cadena.

    Estrategia:
    - Consulta Crossref /works/{doi}
    - Si encuentra un link con content-type que contenga "pdf", lo considera OA
    - Si no hay link pero hay licencia CC, lo marca como OA sin URL directa
    """

    BASE_URL = "https://api.crossref.org/works"

    def __init__(
        self,
        email: str,
        timeout: float = 8.0,
        next_checker: Optional[BaseOpenAccessChecker] = None,
    ):
        """
        Inicializar el checker de Crossref.

        Args:
            email: Email de contacto para User-Agent (recomendado por Crossref)
            timeout: Timeout en segundos para las peticiones HTTP
            next_checker: Siguiente checker de la cadena (Chain of Responsibility)
        """
        super().__init__(next_checker)
        self.email = email
        self.timeout = timeout
        self.headers = {
            "User-Agent": f"ADN4Research/1.0 (mailto:{email})"
        }

    @property
    def source_name(self) -> str:
        """Nombre de la fuente para logging y resultados."""
        return "Crossref"

    def check_access(self, doi: DOI) -> OpenAccessResult:
        """
        Verificar Open Access en Crossref.

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
            resp = requests.get(url, headers=self.headers, timeout=self.timeout)
            
            if resp.status_code != 200:
                logger.debug(f"Crossref OA HTTP {resp.status_code} para {doi.value}")
                return self._pass_to_next(doi)

            data = resp.json()
            item = data.get("message", {}) if isinstance(data, dict) else {}

            # Buscar URL de PDF en los links
            links = item.get("link", []) or []
            pdf_url = None
            
            for link in links:
                ctype = (link.get("content-type") or "").lower()
                url_candidate = link.get("URL")
                if not url_candidate:
                    continue
                if ctype == "application/pdf":
                    pdf_url = url_candidate
                    break
                if "pdf" in ctype and not pdf_url:
                    pdf_url = url_candidate

            # Licencias CC sugieren OA aunque no haya URL directa
            licenses = item.get("license", []) or []
            cc_license = None
            for lic in licenses:
                lic_url = lic.get("URL", "").lower()
                if "creativecommons" in lic_url:
                    cc_license = lic.get("URL")
                    break

            is_oa = bool(pdf_url) or bool(cc_license)

            if is_oa:
                result = OpenAccessResult(
                    is_oa=True,
                    pdf_url=pdf_url,
                    landing_url=None,
                    source=self.source_name,
                    license=cc_license,
                )
                logger.info(f"✅ Open Access encontrado en Crossref: {doi.value}")
                return result

            logger.debug(f"🔒 No OA en Crossref: {doi.value}")
            return self._pass_to_next(doi)

        except requests.Timeout:
            logger.error(f"Timeout al consultar Crossref: {doi.value}")
            return self._pass_to_next(doi)

        except requests.RequestException as e:
            logger.error(f"Error de red con Crossref para {doi.value}: {e}")
            return self._pass_to_next(doi)

        except Exception as exc:
            logger.warning(f"Error consultando Crossref OA para {doi.value}: {exc}")
            return self._pass_to_next(doi)


# Alias para backward compatibility
CrossrefOpenAccessChecker = CrossrefChecker
