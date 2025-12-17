"""
Open Access Checkers - Chain of Responsibility Pattern.

Conectores para verificar si un estudio es Open Access consultando
múltiples fuentes en cadena: Unpaywall -> Crossref -> Scopus.

Uso:
    from apps.acquisition.downloads.adapters.outbound.connectors.oa_checkers import (
        UnpaywallChecker,
        CrossrefChecker,
        ScopusChecker,
    )
    
    # Construir cadena
    scopus = ScopusChecker(api_key="...", next_checker=None)
    crossref = CrossrefChecker(email="...", next_checker=scopus)
    unpaywall = UnpaywallChecker(email="...", next_checker=crossref)
    
    # Usar
    result = unpaywall.check_access(doi)
"""

from .unpaywall_checker import UnpaywallChecker
from .crossref_checker import CrossrefChecker
from .scopus_checker import ScopusChecker

__all__ = [
    "UnpaywallChecker",
    "CrossrefChecker",
    "ScopusChecker",
]
