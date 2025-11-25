from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class QuoteLocation:
    """
    Value Object que representa la ubicación de un quote en el PDF.

    Attributes:
        page: Número de página (1-indexed)
        text_location: Texto descriptivo (ej: "Sección 3.2, párrafo 2")
        coordinates: Coordenadas del rectángulo de selección (opcional)
    """
    page: int
    text_location: str = ""
    x1: Optional[float] = None  # Coordenada X inicio
    y1: Optional[float] = None  # Coordenada Y inicio
    x2: Optional[float] = None  # Coordenada X fin
    y2: Optional[float] = None  # Coordenada Y fin

    def __post_init__(self):
        if self.page < 1:
            raise ValueError("El número de página debe ser mayor a 0")

        coords = [self.x1, self.y1, self.x2, self.y2]
        if any(c is not None for c in coords):
            if not all(c is not None for c in coords):
                raise ValueError(
                    "Las coordenadas deben estar completas (x1, y1, x2, y2)"
                )

    @property
    def has_coordinates(self) -> bool:
        """Indica si tiene coordenadas de selección"""
        return all([
            self.x1 is not None,
            self.y1 is not None,
            self.x2 is not None,
            self.y2 is not None
        ])

    def to_dict(self) -> dict:
        """Serializa a diccionario"""
        return {
            "page": self.page,
            "text_location": self.text_location,
            "coordinates": {
                "x1": self.x1,
                "y1": self.y1,
                "x2": self.x2,
                "y2": self.y2
            } if self.has_coordinates else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'QuoteLocation':
        """Deserializa desde diccionario"""
        coords = data.get('coordinates', {})
        return cls(
            page=data['page'],
            text_location=data.get('text_location', ''),
            x1=coords.get('x1') if coords else None,
            y1=coords.get('y1') if coords else None,
            x2=coords.get('x2') if coords else None,
            y2=coords.get('y2') if coords else None
        )