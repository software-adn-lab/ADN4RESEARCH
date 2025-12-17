from dataclasses import dataclass, field
from typing import List
from .models import PaperExtraction

@dataclass(frozen=True)
class CompletionResult:
    """DTO que encapsula el resultado de intentar completar un paper."""
    success: bool
    paper: PaperExtraction
    errors: List[str] = field(default_factory=list) # Lista de nombres de tags faltantes

    @property
    def message(self) -> str:
        if self.success:
            return "El paper se ha completado exitosamente."
        return f"Faltan etiquetas obligatorias: {', '.join(self.errors)}"