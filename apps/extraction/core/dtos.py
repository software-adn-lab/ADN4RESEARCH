from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from .models import PaperExtraction
from apps.extraction.taxonomy.dtos import TagDTO

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

@dataclass(frozen=True)
class QuoteDTO:
    """DTO para quotes usados en payloads JSON."""
    id: int
    text_fragment: str
    location: Dict[str, Any]
    tags: List[TagDTO]
    created_at: Optional[str] = None

    @classmethod
    def from_model(cls, quote, include_created_at: bool = False) -> "QuoteDTO":
        tags = [TagDTO.from_model(tag) for tag in quote.tags.all()]
        created_at = None
        if include_created_at and quote.created_at:
            created_at = quote.created_at.isoformat()
        return cls(
            id=quote.id,
            text_fragment=quote.text_fragment,
            location=quote.location or {},
            tags=tags,
            created_at=created_at,
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "id": self.id,
            "text_fragment": self.text_fragment,
            "location": self.location,
            "tags": [tag.to_dict() for tag in self.tags],
        }
        if self.created_at:
            payload["created_at"] = self.created_at
        return payload


@dataclass(frozen=True)
class PaperCompletionSummaryDTO:
    """DTO para resumen de completitud de un paper."""
    id: int
    status: str
    quotes_count: int
    coverage_percentage: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "quotes_count": self.quotes_count,
            "coverage_percentage": self.coverage_percentage,
        }
