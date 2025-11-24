"""
CrossrefOpenAccessChecker - Verifica OA y posibles URLs de PDF usando la API de Crossref.

Este checker actúa como respaldo cuando Unpaywall no encuentra OA. Busca enlaces en el
campo `link` de la respuesta de Crossref con content-type PDF, y también señales de licencia
que indiquen acceso abierto.
"""

import logging
from typing import Dict, Any, Optional

import requests

from apps.acquisition.shared.domain.value_objects.doi import DOI

logger = logging.getLogger(__name__)


class CrossrefOpenAccessChecker:
    """
    Checker de Open Access vía Crossref.

    Estrategia:
    - Consulta Crossref /works/{doi}
    - Si encuentra un link con content-type que contenga "pdf", lo considera OA
    - Si no hay link pero hay licencia CC, lo marca como OA sin URL directa
    """

    BASE_URL = "https://api.crossref.org/works"

    def __init__(self, email: str):
        """
        Args:
            email: Email de contacto para User-Agent (recomendado por Crossref)
        """
        self.email = email
        self.headers = {
            "User-Agent": f"ADN4Research/1.0 (mailto:{email})"
        }

    def is_open_access(self, doi: DOI) -> bool:
        """Retorna True si Crossref sugiere que el DOI es OA."""
        info = self.get_oa_info(doi)
        return bool(info.get("is_oa", False))

    def get_oa_info(self, doi: DOI) -> Dict[str, Any]:
        """
        Obtener información OA desde Crossref.

        Returns:
            {
                "is_oa": bool,
                "pdf_url": Optional[str],
                "landing_url": Optional[str],
                "source": "Crossref"
            }
        """
        if not doi or not doi.value:
            return {"is_oa": False, "pdf_url": None, "landing_url": None, "source": "Crossref"}

        try:
            url = f"{self.BASE_URL}/{doi.value}"
            resp = requests.get(url, headers=self.headers, timeout=8)
            if resp.status_code != 200:
                logger.debug(f"Crossref OA HTTP {resp.status_code} para {doi.value}")
                return {"is_oa": False, "pdf_url": None, "landing_url": None, "source": "Crossref"}

            data = resp.json()
            item = data.get("message", {}) if isinstance(data, dict) else {}

            links = item.get("link", []) or []
            pdf_url = None
            # Priorizar application/pdf
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
            has_cc = any("creativecommons" in (lic.get("URL", "").lower()) for lic in licenses)

            is_oa = bool(pdf_url) or has_cc

            return {
                "is_oa": is_oa,
                "pdf_url": pdf_url,
                "landing_url": None,
                "source": "Crossref",
            }

        except Exception as exc:
            logger.warning(f"Error consultando Crossref OA para {doi.value}: {exc}")
            return {"is_oa": False, "pdf_url": None, "landing_url": None, "source": "Crossref"}
