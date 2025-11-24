"""
ConsolidationStatus - Estado de calidad de metadatos.

Define los estados válidos para el proceso de consolidación.
Evita strings mágicos y centraliza la definición.
"""

from enum import Enum


class ConsolidationStatus(str, Enum):
    """
    Estado de la calidad de los metadatos de un estudio.

    COMPLETO: Tiene todos los campos requeridos (title, link, source, doi, year, authors)
    PARCIAL: Tiene campos obligatorios + al menos uno requerido
    FALLIDO: Faltan campos obligatorios o no tiene ningún requerido
    """
    COMPLETO = "completo"
    PARCIAL = "parcial"
    FALLIDO = "fallido"
