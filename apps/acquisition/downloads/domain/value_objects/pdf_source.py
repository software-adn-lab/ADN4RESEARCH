"""
PdfSource - Origen del texto completo obtenido.

Define las fuentes válidas desde donde se obtuvo el PDF.
Evita strings mágicos y centraliza la definición para trazabilidad.
"""

from enum import Enum


class PdfSource(str, Enum):
    """
    Origen del texto completo de un estudio.

    AUTOMATICO: Descargado automáticamente desde fuente Open Access legítima
                (ej: Unpaywall, DOAJ, repositorio institucional)
    ALTERNATIVO: Obtenido desde fuente alternativa después de fallar descarga directa
                 (ej: CORE, ResearchGate, repositorios preprint)
    MANUAL: Subido manualmente por el usuario
    """
    AUTOMATICO = "automático"
    ALTERNATIVO = "alternativo"
    MANUAL = "manual"
