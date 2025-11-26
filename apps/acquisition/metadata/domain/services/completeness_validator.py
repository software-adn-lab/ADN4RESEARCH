"""
CompletenessValidator - Servicio de validación de completitud de metadatos.

Responsabilidad única: Determinar el estado de consolidación de un estudio
basándose en la presencia/ausencia de campos requeridos.

Estados posibles:
- COMPLETO: Tiene todos los campos requeridos
- PARCIAL: Tiene campos obligatorios + al menos uno requerido
- FALLIDO: Faltan campos obligatorios o no tiene ningún requerido
"""

from typing import List, Dict, Set
from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.metadata.domain.value_objects.consolidation_status import ConsolidationStatus


class CompletenessValidator:
    """
    Servicio de dominio que determina la calidad de los metadatos de un estudio.

    Reglas de negocio:
    - Campos OBLIGATORIOS (sin ellos es FALLIDO): title, link, source
    - Campos REQUERIDOS (para estar COMPLETO): doi, year, authors
    - Campos DESEABLES (no afectan estado): abstract, journal, keywords
    """

    OBLIGATORY_FIELDS: Set[str] = {"title", "link", "source"}
    REQUIRED_FIELDS: Set[str] = {"doi", "year", "authors"}
    DESIRABLE_FIELDS: Set[str] = {"abstract", "journal", "keywords"}

    def validate(self, study: Study) -> ConsolidationStatus:
        """
        Evalúa el estudio y retorna su estado de consolidación.

        Args:
            study: Estudio a evaluar

        Returns:
            ConsolidationStatus indicando la calidad de los metadatos

        Examples:
            >>> validator = CompletenessValidator()
            >>> # Estudio con todo
            >>> validator.validate(study_complete)
            ConsolidationStatus.COMPLETO
            >>> # Estudio sin DOI
            >>> validator.validate(study_no_doi)
            ConsolidationStatus.PARCIAL
        """
        missing = self.get_missing_fields(study)
        missing_set = set(missing)

        # 1. Verificar campos obligatorios
        missing_obligatory = missing_set & self.OBLIGATORY_FIELDS
        if missing_obligatory:
            return ConsolidationStatus.FALLIDO

        # 2. Verificar campos requeridos
        missing_required = missing_set & self.REQUIRED_FIELDS
        present_required = self.REQUIRED_FIELDS - missing_required

        # Si tiene todos los requeridos -> COMPLETO
        if not missing_required:
            return ConsolidationStatus.COMPLETO

        # Si tiene al menos uno de los requeridos -> PARCIAL
        if present_required:
            return ConsolidationStatus.PARCIAL

        # No tiene ningún requerido -> FALLIDO
        return ConsolidationStatus.FALLIDO

    def get_missing_fields(self, study: Study) -> List[str]:
        """
        Retorna lista de campos faltantes en el estudio.

        Args:
            study: Estudio a analizar

        Returns:
            Lista de nombres de campos que están vacíos/nulos
        """
        missing = []

        # Campos obligatorios
        if not self._has_value(study.title):
            missing.append("title")
        if not self._has_value(study.link):
            missing.append("link")
        if not self._has_source(study):
            missing.append("source")

        # Campos requeridos
        if not self._has_doi(study):
            missing.append("doi")
        if not self._has_value(study.year):
            missing.append("year")
        if not self._has_authors(study):
            missing.append("authors")

        # Campos deseables
        if not self._has_value(study.abstract):
            missing.append("abstract")
        if not self._has_value(study.journal):
            missing.append("journal")
        if not self._has_keywords(study):
            missing.append("keywords")

        return missing

    def get_present_fields(self, study: Study) -> List[str]:
        """
        Retorna lista de campos presentes en el estudio.

        Args:
            study: Estudio a analizar

        Returns:
            Lista de nombres de campos que tienen valor
        """
        all_fields = (
            self.OBLIGATORY_FIELDS |
            self.REQUIRED_FIELDS |
            self.DESIRABLE_FIELDS
        )
        missing = set(self.get_missing_fields(study))
        return list(all_fields - missing)

    def get_validation_summary(self, study: Study) -> Dict[str, any]:
        """
        Retorna un resumen detallado de la validación.

        Args:
            study: Estudio a analizar

        Returns:
            Diccionario con información detallada de la validación
        """
        missing = self.get_missing_fields(study)
        missing_set = set(missing)

        return {
            "status": self.validate(study).value,
            "missing_fields": missing,
            "present_fields": self.get_present_fields(study),
            "missing_obligatory": list(missing_set & self.OBLIGATORY_FIELDS),
            "missing_required": list(missing_set & self.REQUIRED_FIELDS),
            "missing_desirable": list(missing_set & self.DESIRABLE_FIELDS),
            "is_usable": self.validate(study) != ConsolidationStatus.FALLIDO,
        }

    def _has_value(self, value) -> bool:
        """Verifica si un valor está presente y no vacío."""
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        return True

    def _has_doi(self, study: Study) -> bool:
        """Verifica si el estudio tiene DOI válido."""
        if not study.doi:
            return False
        return bool(study.doi.value and study.doi.value.strip())

    def _has_source(self, study: Study) -> bool:
        """Verifica si el estudio tiene source válido."""
        if not study.source:
            return False
        return bool(study.source.name and study.source.name.strip())

    def _has_authors(self, study: Study) -> bool:
        """Verifica si el estudio tiene autores válidos."""
        if not study.authors:
            return False
        return any(author and author.strip() for author in study.authors)

    def _has_keywords(self, study: Study) -> bool:
        """Verifica si el estudio tiene keywords válidos."""
        if not study.keywords:
            return False
        return any(kw and kw.strip() for kw in study.keywords)
