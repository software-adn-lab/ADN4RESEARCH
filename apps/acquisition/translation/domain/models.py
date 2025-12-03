"""
Modelos de dominio para estrategias de búsqueda normalizadas.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from apps.acquisition.shared.domain.exceptions import DomainValidationError


@dataclass(frozen=True)
class MainTerm:
    """
    Término principal de búsqueda con sus sinónimos.

    Inmutable por diseño (frozen=True).
    """
    term: str
    synonyms: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validar reglas de negocio."""
        if not self.term or not self.term.strip():
            raise DomainValidationError("term", "El término no puede estar vacío")

    @classmethod
    def from_dict(cls, data: dict) -> 'MainTerm':
        """
        Crear MainTerm desde diccionario.

        Args:
            data: {"term": str, "synonyms": [str]}

        Raises:
            DomainValidationError: Si falta 'term' o está vacío
        """
        if "term" not in data:
            raise DomainValidationError("term", "El campo 'term' es obligatorio")

        term = data["term"].strip() if isinstance(data["term"], str) else ""

        raw_synonyms = data.get("synonyms", [])
        synonyms = list(dict.fromkeys(
            s.strip() for s in raw_synonyms if s and isinstance(s, str) and s.strip()
        ))

        return cls(term=term, synonyms=synonyms)

    def to_dict(self) -> dict:
        """Serializar a diccionario."""
        return {
            "term": self.term,
            "synonyms": self.synonyms
        }


@dataclass(frozen=True)
class YearFilter:
    """
    Filtro de rango de años.

    Inmutable por diseño (frozen=True).
    """
    year_from: int
    year_to: int

    def __post_init__(self):
        """Validar reglas de negocio."""
        if self.year_from > self.year_to:
            raise DomainValidationError(
                "filters.year",
                f"'from' ({self.year_from}) no puede ser mayor que 'to' ({self.year_to})"
            )

    @classmethod
    def from_dict(cls, data: dict) -> 'YearFilter':
        """
        Crear YearFilter desde diccionario.

        Args:
            data: {"from": int, "to": int}

        Raises:
            DomainValidationError: Si falta 'from'/'to' o no son enteros
        """
        if "from" not in data:
            raise DomainValidationError("filters.year", "El campo 'from' es obligatorio")
        if "to" not in data:
            raise DomainValidationError("filters.year", "El campo 'to' es obligatorio")

        try:
            year_from = int(data["from"])
        except (ValueError, TypeError):
            raise DomainValidationError("filters.year.from", "Debe ser un entero")

        try:
            year_to = int(data["to"])
        except (ValueError, TypeError):
            raise DomainValidationError("filters.year.to", "Debe ser un entero")

        return cls(year_from=year_from, year_to=year_to)

    def to_dict(self) -> dict:
        """Serializar a diccionario."""
        return {
            "from": self.year_from,
            "to": self.year_to
        }


@dataclass(frozen=True)
class NormalizedStrategy:
    """
    Estrategia de búsqueda normalizada e inmutable.

    Representa la entrada de negocio validada para el proceso de traducción.

    Atributos:
        main_terms: Lista de términos principales con sus sinónimos (≥1)
        exclusions: Lista de términos a excluir (puede estar vacía)
        year_filter: Filtro de rango de años (opcional)

    Invariantes de dominio:
        - main_terms debe tener al menos un elemento
        - Cada main_term.term no puede estar vacío
        - Si year_filter existe, from <= to
        - La instancia es inmutable (frozen=True)
    """

    main_terms: List[MainTerm]
    exclusions: List[str] = field(default_factory=list)
    year_filter: Optional[YearFilter] = None

    def __post_init__(self):
        """Validar invariantes de dominio."""
        if not self.main_terms:
            raise DomainValidationError("main_terms", "Debe tener al menos un término")

    @classmethod
    def from_dict(cls, data: dict) -> 'NormalizedStrategy':
        """
        Crear NormalizedStrategy desde diccionario.

        Args:
            data: Diccionario con estructura esperada

        Returns:
            NormalizedStrategy validada e inmutable

        Raises:
            DomainValidationError: Si alguna regla de negocio se viola
        """
        if "main_terms" not in data:
            raise DomainValidationError("main_terms", "El campo es obligatorio")

        main_terms_data = data.get("main_terms", [])
        if not isinstance(main_terms_data, list):
            raise DomainValidationError("main_terms", "Debe ser una lista")

        try:
            main_terms = [MainTerm.from_dict(item) for item in main_terms_data]
        except DomainValidationError:
            raise
        except Exception as e:
            raise DomainValidationError("main_terms", f"Error al parsear: {str(e)}")

        exclusions_data = data.get("exclusions", [])
        if not isinstance(exclusions_data, list):
            raise DomainValidationError("exclusions", "Debe ser una lista")

        exclusions = [
            exc.strip()
            for exc in exclusions_data
            if exc and isinstance(exc, str) and exc.strip()
        ]

        year_filter = None
        filters_data = data.get("filters", {})
        if filters_data and "year" in filters_data:
            year_filter = YearFilter.from_dict(filters_data["year"])

        return cls(
            main_terms=main_terms,
            exclusions=exclusions,
            year_filter=year_filter
        )

    def to_dict(self) -> dict:
        """
        Serializar a diccionario.

        Returns:
            Diccionario con la misma estructura que from_dict acepta
        """
        result = {
            "main_terms": [mt.to_dict() for mt in self.main_terms],
            "exclusions": self.exclusions,
        }

        if self.year_filter:
            result["filters"] = {
                "year": self.year_filter.to_dict()
            }

        return result

    def __eq__(self, other) -> bool:
        """
        Comparación por valor (para verificar inmutabilidad).

        Dos NormalizedStrategy con los mismos datos son iguales.
        """
        if not isinstance(other, NormalizedStrategy):
            return False

        return (
            self.main_terms == other.main_terms
            and self.exclusions == other.exclusions
            and self.year_filter == other.year_filter
        )

    def __hash__(self) -> int:
        """
        Hash basado en valor (necesario para frozen=True).
        """
        return hash((
            self.strategy_id,
            tuple(self.main_terms),
            tuple(self.exclusions),
            self.year_filter
        ))
