"""
ScopusInstitutionalChecker - Verifica OA/links usando la API oficial de Scopus (Elsevier).

Se usa como último recurso legal para estudios de Scopus cuando Unpaywall/Crossref
no encontraron OA, aprovechando la suscripción institucional si existe.
"""

import logging
from typing import Dict, Any, Optional

import requests

from apps.acquisition.shared.domain.value_objects.doi import DOI

logger = logging.getLogger(__name__)


class ScopusInstitutionalChecker:
    """
    Checker de Open Access usando la API de Scopus.

    Estrategia:
    - Consulta abstract por DOI con apiKey institucional
    - Evalúa flag de open access si está disponible
    - Retorna landing_url hacia el publisher cuando no hay PDF directo
    """

    BASE_URL = "https://api.elsevier.com/content/abstract/doi"

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Se requiere SCOPUS_API_KEY para ScopusInstitutionalChecker")
        self.api_key = api_key

    def is_open_access(self, doi: DOI, study=None) -> bool:
        info = self.get_oa_info(doi)
        return bool(info.get("is_oa", False))

    def get_oa_info(self, doi: DOI) -> Dict[str, Any]:
        """
        Consulta Scopus Abstract API por DOI y extrae señales de OA.

        Returns:
            {
                "is_oa": bool,
                "pdf_url": Optional[str],
                "landing_url": Optional[str],
                "source": "Scopus"
            }
        """
        if not doi or not doi.value:
            return {"is_oa": False, "pdf_url": None, "landing_url": None, "source": "Scopus"}

        try:
            url = f"{self.BASE_URL}/{doi.value}"
            headers = {
                "X-ELS-APIKey": self.api_key,
                "Accept": "application/json",
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                logger.debug(f"Scopus OA HTTP {resp.status_code} para {doi.value}")
                return {"is_oa": False, "pdf_url": None, "landing_url": None, "source": "Scopus"}

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

            # Links disponibles
            links = core.get("link", []) or []
            landing_url = None
            pdf_url = None

            for link in links:
                rel = (link.get("@rel") or "").lower()
                href = link.get("@href")
                if not href:
                    continue
                # link "@rel": "scidir" suele ser landing en ScienceDirect (con suscripción)
                if rel == "scidir" and not landing_url:
                    landing_url = href
                # No suele venir PDF directo, pero por si acaso
                if "pdf" in rel or (link.get("@type") or "").lower() == "application/pdf":
                    pdf_url = href
                    break

            return {
                "is_oa": is_oa,
                "pdf_url": pdf_url,
                "landing_url": landing_url,
                "source": "Scopus",
            }

        except Exception as exc:
            logger.warning(f"Error consultando Scopus OA para {doi.value}: {exc}")
            return {"is_oa": False, "pdf_url": None, "landing_url": None, "source": "Scopus"}
