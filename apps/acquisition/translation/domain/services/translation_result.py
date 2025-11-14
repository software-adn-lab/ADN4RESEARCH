"""
DTO para resultados de traducción de estrategias.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass(frozen=True)
class TranslationResult:
    """
    Resultado inmutable de traducir una estrategia normalizada.

    Este DTO encapsula todo lo que un traductor de dominio produce:
    - La query traducida
    - Advertencias (si las hay)
    - Pasos aplicados (para trazabilidad)
    - Reglas aplicadas (para auditoría)
    - Metadata adicional

    Atributos:
        query: Query traducida en el dialecto del target
        warnings: Lista de advertencias (vacía si no hay)
        steps_applied: Pasos ejecutados en el proceso de traducción
        rules_applied: Reglas de negocio aplicadas
        metadata: Información adicional (ej: year_filter separado para IEEE)
    """

    query: str
    warnings: List[str] = field(default_factory=list)
    steps_applied: List[str] = field(default_factory=list)
    rules_applied: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
