"""
ManualStudyService - Servicio de aplicación para registro manual de estudios.
"""

from typing import Optional, List

from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.shared.domain.repositories.i_study_repository import IStudyRepository
from apps.acquisition.shared.domain.value_objects.doi import DOI


class ManualStudyService:
    """Servicio de aplicación para crear estudios manualmente."""

    def __init__(self, repository: IStudyRepository):
        """Inicializar el servicio."""
        self.repository = repository

    def create_manual_study(
        self,
        title: str,
        link: str,
        doi: Optional[str] = None,
        authors: Optional[List[str]] = None,
        abstract: Optional[str] = None,
        year: Optional[int] = None,
        journal: Optional[str] = None,
        keywords: Optional[List[str]] = None,
    ) -> Study:
        """
        Crear un estudio manualmente con persistencia.

        Args:
            title: Título del estudio (obligatorio)
            link: URL del estudio (obligatorio)
            doi: DOI del estudio (opcional)
            authors: Lista de autores (opcional)
            abstract: Resumen del estudio (opcional)
            year: Año de publicación (opcional)
            journal: Revista/Conferencia (opcional)
            keywords: Palabras clave (opcional)

        Returns:
            Study creado y persistido

        Raises:
            ValueError: Si faltan campos obligatorios o son inválidos
        """
        if not title or not title.strip():
            raise ValueError("El título es obligatorio")

        if not link or not link.strip():
            raise ValueError("El link es obligatorio")

        doi_obj = None
        if doi:
            try:
                doi_obj = DOI(doi)
            except Exception as e:
                raise ValueError(f"DOI inválido: {e}")

        study = Study.create_discovered(
            title=title.strip(),
            link=link.strip(),
            source="Manual",
            doi=doi_obj,
        )

        if authors:
            study.authors = authors

        if abstract:
            study.abstract = abstract.strip()

        if year is not None:
            if not (1900 <= year <= 2100):
                raise ValueError(f"Año inválido: {year}")
            study.year = year

        if journal:
            study.journal = journal.strip()

        if keywords:
            study.keywords = keywords

        study.field_origins["title"] = "manual"
        study.field_origins["link"] = "manual"
        study.field_origins["source"] = "manual"

        if doi:
            study.field_origins["doi"] = "manual"
        if authors:
            study.field_origins["authors"] = "manual"
        if abstract:
            study.field_origins["abstract"] = "manual"
        if year:
            study.field_origins["year"] = "manual"
        if journal:
            study.field_origins["journal"] = "manual"
        if keywords:
            study.field_origins["keywords"] = "manual"

        saved_study = self.repository.save(study)
        return saved_study
