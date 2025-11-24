from dataclasses import dataclass, field
from typing import List, Optional
from .tag import Tag
from ..value_objects.quote_location import QuoteLocation


@dataclass
class Quote:
    """
    Entidad secundaria.
    Representa un fragmento extraído. Su ciclo de vida depende de Extraction.
    """
    id: Optional[int]
    extraction_id: int
    text: str
    researcher_id: int
    tags: List[Tag] = field(default_factory=list)
    location: Optional[QuoteLocation] = None

    def add_tag(self, tag: Tag):
        if not any(t.id == tag.id for t in self.tags):
            self.tags.append(tag)

    def replace_tag(self, old_tag: Tag, new_tag: Tag):
        """
        Reemplaza una etiqueta por otra.
        Si la nueva ya existe, solo elimina la vieja.
        """
        self.tags = [t for t in self.tags if t.id != old_tag.id]

        self.add_tag(new_tag)

    def update_location(
            self,
            page: int,
            text_location: str = "",
            x1: Optional[float] = None,
            y1: Optional[float] = None,
            x2: Optional[float] = None,
            y2: Optional[float] = None
    ):
        """
        Actualiza la ubicación del quote en el PDF.

        Args:
            page: Número de página
            text_location: Descripción textual
            x1, y1, x2, y2: Coordenadas del rectángulo de selección
        """
        self.location = QuoteLocation(
            page=page,
            text_location=text_location,
            x1=x1, y1=y1, x2=x2, y2=y2
        )

    @property
    def page_number(self) -> Optional[int]:
        """Retorna el número de página si existe"""
        return self.location.page if self.location else None