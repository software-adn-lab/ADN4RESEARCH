"""
Conectores a fuentes externas para descarga de PDFs.

Estructura de subcarpetas:
- oa_checkers/: Chain of Responsibility para verificación de Open Access
- downloaders/: HttpDownloader y SciHubDownloader
- alternative/: AlternativeSourceFinder
- cache/: DownloadCache para evitar re-descargas

Patrón Chain of Responsibility:
Los checkers de Open Access (Unpaywall, Crossref, Scopus) heredan de
BaseOpenAccessChecker y pueden encadenarse para verificar OA en secuencia.

Ejemplo de uso:
    from apps.acquisition.downloads.adapters.outbound.connectors import (
        UnpaywallChecker,
        CrossrefChecker,  # Nombre corto
        ScopusChecker,    # Nombre corto
    )
    
    # Configurar la cadena
    scopus = ScopusChecker(api_key="...", next_checker=None)
    crossref = CrossrefChecker(email="...", next_checker=scopus)
    unpaywall = UnpaywallChecker(email="...", next_checker=crossref)
    
    # Usar el primer eslabón
    result = unpaywall.check_access(doi)  # Retorna OpenAccessResult
"""

# ============================================================================
# OA Checkers - Chain of Responsibility
# ============================================================================
from .oa_checkers import (
    UnpaywallChecker,
    CrossrefChecker,
    ScopusChecker,
)

# Aliases para backward compatibility
CrossrefOpenAccessChecker = CrossrefChecker
ScopusInstitutionalChecker = ScopusChecker

# ============================================================================
# Downloaders
# ============================================================================
from .downloaders import (
    HttpDownloader,
    SciHubDownloader,
)

# ============================================================================
# Alternative Sources
# ============================================================================
from .alternative import (
    AlternativeSourceFinder,
)

# ============================================================================
# Cache
# ============================================================================
from .cache import (
    DownloadCache,
)

# ============================================================================
# Re-exportar interfaces desde domain para conveniencia
# ============================================================================
from apps.acquisition.downloads.domain.interfaces import (
    BaseOpenAccessChecker,
    OpenAccessResult,
)

__all__ = [
    # OA Checkers (nuevos nombres cortos)
    "UnpaywallChecker",
    "CrossrefChecker",
    "ScopusChecker",
    # Aliases backward compatibility
    "CrossrefOpenAccessChecker",
    "ScopusInstitutionalChecker",
    # Base e interfaces
    "BaseOpenAccessChecker",
    "OpenAccessResult",
    # Downloaders
    "HttpDownloader",
    "SciHubDownloader",
    # Alternative
    "AlternativeSourceFinder",
    # Cache
    "DownloadCache",
]
