"""
DjangoStudyRepository - Implementación del repositorio usando Django ORM.

Este adaptador es el PUENTE entre el Dominio (entidad Study) y la Infraestructura (Django ORM).

Responsabilidades:
- Mapear Entidad de Dominio → Modelo Django (para escribir)
- Mapear Modelo Django → Entidad de Dominio (para leer)
- Implementar todas las operaciones definidas en IStudyRepository
"""

from typing import List, Optional
from datetime import datetime

from apps.acquisition.shared.domain.repositories.i_study_repository import IStudyRepository
from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.shared.domain.value_objects.study_status import StudyStatus
from apps.acquisition.shared.domain.value_objects.doi import DOI
from apps.acquisition.shared.domain.value_objects.source import Source

# Django ORM model
from apps.acquisition.models import StudyModel


class DjangoStudyRepository(IStudyRepository):
    """
    Implementación del repositorio usando Django ORM.

    Sigue el patrón Repository de DDD: abstrae la persistencia
    y mantiene el dominio limpio de detalles de infraestructura.
    """

    # =========================================================================
    # MAPPERS: Conversión entre Modelo Django y Entidad de Dominio
    # =========================================================================

    def _to_entity(self, model: StudyModel) -> Study:
        """
        Mapea Modelo Django → Entidad de Dominio.

        Args:
            model: Instancia del modelo Django ORM

        Returns:
            Instancia de la entidad de dominio Study
        """
        return Study.from_dict({
            "id": str(model.uuid),
            "title": model.title,
            "link": model.link,
            "source": model.source,
            "doi": model.doi,
            "status": model.status,
            "authors": model.authors,
            "abstract": model.abstract,
            "year": model.year,
            "journal": model.journal,
            "keywords": model.keywords,
            "pdf_path": model.pdf_path,
            "pdf_source": model.pdf_source,
            "download_status": model.download_status,
            "discovered_at": model.discovered_at.isoformat() if model.discovered_at else None,
            "enriched_at": model.enriched_at.isoformat() if model.enriched_at else None,
            "downloaded_at": model.downloaded_at.isoformat() if model.downloaded_at else None,
            "failure_reason": model.failure_reason,
            "consolidation_status": model.consolidation_status,
            "field_origins": model.field_origins,
        })

    def _to_model_dict(self, study: Study) -> dict:
        """
        Mapea Entidad de Dominio → Dict para Django ORM.

        Args:
            study: Instancia de la entidad de dominio

        Returns:
            Diccionario con los campos para crear/actualizar el modelo Django
        """
        return {
            "uuid": study.id,
            "title": study.title,
            "link": study.link,
            "source": study.source.name,
            "doi": study.doi.value if study.doi else None,
            "status": study.status.value,
            "authors": study.authors,
            "abstract": study.abstract,
            "year": study.year,
            "journal": study.journal,
            "keywords": study.keywords,
            "pdf_path": study.pdf_path,
            "pdf_source": study.pdf_source,
            "download_status": study.download_status,
            "discovered_at": study.discovered_at,
            "enriched_at": study.enriched_at,
            "downloaded_at": study.downloaded_at,
            "failure_reason": study.failure_reason,
            "consolidation_status": study.consolidation_status,
            "field_origins": study.field_origins,
        }

    # =========================================================================
    # IMPLEMENTACIÓN DE IStudyRepository
    # =========================================================================

    def save(self, study: Study) -> Study:
        """
        Guardar un estudio (crear o actualizar).

        Usa update_or_create de Django para garantizar idempotencia.
        """
        data = self._to_model_dict(study)
        uuid = data.pop("uuid")

        model, created = StudyModel.objects.update_or_create(
            uuid=uuid,
            defaults=data
        )

        return self._to_entity(model)

    def save_batch(self, studies: List[Study]) -> List[Study]:
        """
        Guardar múltiples estudios en batch (optimizado).

        Usa bulk_create con update_conflicts para performance.
        """
        if not studies:
            return []

        models_to_create = []
        for study in studies:
            data = self._to_model_dict(study)
            model = StudyModel(**data)
            models_to_create.append(model)

        # bulk_create con update en caso de conflicto (upsert)
        StudyModel.objects.bulk_create(
            models_to_create,
            update_conflicts=True,
            update_fields=[
                "title", "link", "source", "doi", "status",
                "authors", "abstract", "year", "journal", "keywords",
                "pdf_path", "pdf_source", "download_status",
                "enriched_at", "downloaded_at", "failure_reason",
                "consolidation_status", "field_origins",
            ],
            unique_fields=["uuid"],
        )

        # Recuperar los objetos guardados para retornar con IDs actualizados
        uuids = [study.id for study in studies]
        saved_models = StudyModel.objects.filter(uuid__in=uuids)

        return [self._to_entity(model) for model in saved_models]

    def find_by_id(self, study_id: str) -> Optional[Study]:
        """Buscar un estudio por su ID (UUID)."""
        try:
            model = StudyModel.objects.get(uuid=study_id)
            return self._to_entity(model)
        except StudyModel.DoesNotExist:
            return None

    def find_by_doi(self, doi: str) -> Optional[Study]:
        """Buscar un estudio por su DOI."""
        try:
            model = StudyModel.objects.get(doi__iexact=doi)
            return self._to_entity(model)
        except StudyModel.DoesNotExist:
            return None
        except StudyModel.MultipleObjectsReturned:
            # Si hay duplicados, retornar el más reciente
            model = StudyModel.objects.filter(doi__iexact=doi).order_by("-discovered_at").first()
            return self._to_entity(model) if model else None

    def find_by_title_and_source(self, title: str, source: str) -> Optional[Study]:
        """
        Buscar un estudio por título y fuente.

        Útil para deduplicación durante el discovery.
        """
        try:
            model = StudyModel.objects.get(title__iexact=title, source__iexact=source)
            return self._to_entity(model)
        except StudyModel.DoesNotExist:
            return None
        except StudyModel.MultipleObjectsReturned:
            # Si hay duplicados, retornar el más reciente
            model = StudyModel.objects.filter(
                title__iexact=title,
                source__iexact=source
            ).order_by("-discovered_at").first()
            return self._to_entity(model) if model else None

    def find_all_by_status(self, status: StudyStatus) -> List[Study]:
        """Obtener todos los estudios con un estado específico."""
        models = StudyModel.objects.filter(status=status.value)
        return [self._to_entity(model) for model in models]

    def find_all(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Study]:
        """
        Obtener todos los estudios con paginación opcional.

        Args:
            limit: Número máximo de resultados (None = sin límite)
            offset: Número de resultados a saltar (None = desde el inicio)
        """
        queryset = StudyModel.objects.all().order_by("-discovered_at")

        if offset is not None:
            queryset = queryset[offset:]

        if limit is not None:
            queryset = queryset[:limit]

        return [self._to_entity(model) for model in queryset]

    def count_by_status(self, status: StudyStatus) -> int:
        """Contar estudios por estado."""
        return StudyModel.objects.filter(status=status.value).count()

    def delete(self, study_id: str) -> bool:
        """
        Eliminar un estudio por su ID.

        Returns:
            True si se eliminó, False si no existía
        """
        deleted_count, _ = StudyModel.objects.filter(uuid=study_id).delete()
        return deleted_count > 0

    def exists_by_doi(self, doi: str) -> bool:
        """Verificar si existe un estudio con un DOI específico."""
        return StudyModel.objects.filter(doi__iexact=doi).exists()

    def exists_by_title_and_source(self, title: str, source: str) -> bool:
        """
        Verificar si existe un estudio con título y fuente específicos.

        Útil para deduplicación rápida sin cargar toda la entidad.
        """
        return StudyModel.objects.filter(
            title__iexact=title,
            source__iexact=source
        ).exists()
