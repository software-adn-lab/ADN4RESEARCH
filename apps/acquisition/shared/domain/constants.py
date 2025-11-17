"""
Constantes compartidas del dominio de Acquisition.

Este módulo centraliza literales y configuraciones que deben ser
consistentes en todo el módulo (servicios, steps, tests).
"""

from typing import Literal


# ============================================================================
# FUENTES ACADÉMICAS SOPORTADAS
# ============================================================================

# Lista canónica de fuentes soportadas
# ÚNICA FUENTE DE VERDAD para literales de fuentes
SUPPORTED_SOURCES: list[str] = [
    "Scopus",
    "IEEE Xplore"
]

# Type hint para validación estática
SupportedSource = Literal["Scopus", "IEEE Xplore"]


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
