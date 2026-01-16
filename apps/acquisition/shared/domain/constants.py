"""
Constantes compartidas del dominio de Acquisition.

Este módulo centraliza literales y configuraciones que deben ser
consistentes en todo el módulo (servicios, steps, tests).
"""

from typing import Literal


# ============================================================================
# FUENTES ACADÉMICAS SOPORTADAS
# ============================================================================

# Fuentes para DISCOVERY automático (tienen conector de búsqueda)
DISCOVERY_SOURCES: list[str] = [
    "Scopus",
    "IEEE Xplore"
]

# Lista canónica de fuentes soportadas para ESTUDIOS
# Incluye fuentes de discovery + fuentes de enriquecimiento + manual
SUPPORTED_SOURCES: list[str] = [
    "Scopus",
    "IEEE Xplore",
    "Crossref",      # Para enriquecimiento y estudios importados
    "Manual"         # Para estudios agregados manualmente por el usuario
]

# Type hint para validación estática
SupportedSource = Literal["Scopus", "IEEE Xplore", "Crossref", "Manual"]


# ============================================================================
# ESTADOS DE TRADUCCIÓN
# ============================================================================

# Estados posibles para una traducción
TRANSLATION_STATUS_READY = "ready"
TRANSLATION_STATUS_NOT_SUPPORTED = "not_supported"

# Type hint para validación estática
TranslationStatus = Literal["ready", "not_supported"]


# ============================================================================
# ESTADOS DE RESULTADO DE DESCUBRIMIENTO
# ============================================================================

# Resultado: todas las fuentes consultadas exitosamente
DISCOVERY_RESULT_COMPLETE = "complete"

# Resultado: al menos una fuente no pudo ser consultada
DISCOVERY_RESULT_PARTIAL = "partial"

# Type hint para validación estática
DiscoveryResultStatus = Literal["complete", "partial"]


# ============================================================================
# ALIASES DE FUENTES (Solo para traducción UI → Dominio en Facade)
# ============================================================================

# Mapeo de nombres UI → nombres internos canónicos
# Uso: SOLO en el Facade (boundary), no contaminar el dominio
SOURCE_ALIASES: dict[str, str] = {
    # IEEE variantes (UI puede enviar cualquiera de estas)
    "IEEE": "IEEE Xplore",
    "ieee": "IEEE Xplore",
    "IEEE Xplore": "IEEE Xplore",
    "ieee xplore": "IEEE Xplore",
    "ieee-xplore": "IEEE Xplore",
    # Scopus variantes
    "Scopus": "Scopus",
    "scopus": "Scopus",
    "SCOPUS": "Scopus",
}


def normalize_source_names(sources: list[str] | None) -> list[str]:
    """
    Normaliza una lista de nombres de fuentes UI a nombres internos canónicos.
    
    Esta función actúa como BOUNDARY entre la UI y el dominio:
    - Acepta nombres "amigables" de UI ("IEEE", "scopus")
    - Retorna nombres canónicos del dominio ("IEEE Xplore", "Scopus")
    - Si la lista está vacía o es None, retorna TODAS las fuentes de discovery
    
    Args:
        sources: Lista de nombres como vienen de UI (puede ser None o vacío)
        
    Returns:
        Lista de nombres canónicos (solo fuentes válidas de DISCOVERY_SOURCES)
        
    Examples:
        >>> normalize_source_names(["IEEE", "Scopus"])
        ["IEEE Xplore", "Scopus"]
        
        >>> normalize_source_names(None)
        ["Scopus", "IEEE Xplore"]  # Todas las fuentes
        
        >>> normalize_source_names(["ieee"])
        ["IEEE Xplore"]
    """
    if not sources:
        return list(DISCOVERY_SOURCES)
    
    normalized = []
    for s in sources:
        # Buscar en aliases, si no existe usar el nombre tal cual
        canonical = SOURCE_ALIASES.get(s, s)
        # Solo agregar si es una fuente válida de discovery y no está duplicada
        if canonical in DISCOVERY_SOURCES and canonical not in normalized:
            normalized.append(canonical)
    
    # Si después de normalizar no hay fuentes válidas, retornar todas
    return normalized if normalized else list(DISCOVERY_SOURCES)

