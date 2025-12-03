"""
DownloadStatus - Estado de disponibilidad de texto completo.

Define los estados válidos para el proceso de descarga de PDFs.
Evita strings mágicos y centraliza la definición.
"""

from enum import Enum


class DownloadStatus(str, Enum):
    """
    Estado de la disponibilidad del texto completo de un estudio.

    DISPONIBLE: El PDF fue obtenido exitosamente (automático, alternativo o manual)
    NO_DISPONIBLE: No se pudo obtener el PDF en ninguna fuente
    PENDIENTE: Aún no se ha intentado obtener el PDF
    """
    DISPONIBLE = "texto_completo_disponible"
    NO_DISPONIBLE = "no_disponible"
    PENDIENTE = "pendiente"
