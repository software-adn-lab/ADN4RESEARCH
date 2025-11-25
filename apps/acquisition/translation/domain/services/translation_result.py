"""
DTO para resultados de traducción de estrategias.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass(frozen=True)
class TranslationResult:
    """Resultado inmutable de traducir una estrategia normalizada."""

    query: str
    warnings: List[str] = field(default_factory=list)
    steps_applied: List[str] = field(default_factory=list)
    rules_applied: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
