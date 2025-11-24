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
