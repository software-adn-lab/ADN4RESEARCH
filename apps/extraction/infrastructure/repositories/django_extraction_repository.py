from typing import Optional, List
from django.db import transaction
from ...domain.repositories.i_extraction_repository import IExtractionRepository
from ...domain.entities.extraction import Extraction
from ..models import ExtractionModel
from ..mappers.domain_mappers import ExtractionMapper


class DjangoExtractionRepository(IExtractionRepository):

    def get_all_by_study_id(self, study_id: int) -> List[Extraction]:
        """Obtiene todas las extracciones de un estudio"""
        qs = ExtractionModel.objects.prefetch_related(
            'quotes__tags'
        ).filter(study_id=study_id).order_by('extraction_order')

        return [ExtractionMapper.to_domain(m) for m in qs]

    def get_by_study_and_user(self, study_id: int, user_id: int) -> Optional[Extraction]:
        """Obtiene la extracción de un usuario para un estudio específico"""
        try:
            model = ExtractionModel.objects.prefetch_related(
                'quotes__tags'
            ).get(study_id=study_id, assigned_to_id=user_id)

            return ExtractionMapper.to_domain(model)
        except ExtractionModel.DoesNotExist:
            return None

    def get_by_id(self, extraction_id: int) -> Optional[Extraction]:
        try:
            model = ExtractionModel.objects.prefetch_related(
                'quotes__tags'
            ).get(pk=extraction_id)
            return ExtractionMapper.to_domain(model)
        except ExtractionModel.DoesNotExist:
            return None

    def get_by_study_id(self, study_id: int) -> Optional[Extraction]:
        try:
            model = ExtractionModel.objects.prefetch_related(
                'quotes__tags'
            ).get(study_id=study_id)
            return ExtractionMapper.to_domain(model)
        except ExtractionModel.DoesNotExist:
            return None

    @transaction.atomic
    def save(self, extraction: Extraction) -> Extraction:
        data = ExtractionMapper.to_db(extraction)

        if extraction.id:
            ExtractionModel.objects.filter(pk=extraction.id).update(**data)
            model = ExtractionModel.objects.prefetch_related(
                'quotes__tags'
            ).get(pk=extraction.id)
        else:
            model = ExtractionModel.objects.create(**data)
            extraction.id = model.id

        return ExtractionMapper.to_domain(model)

    def list_by_user(
            self,
            user_id: int,
            include_quotes: bool = False
    ) -> List[Extraction]:
        qs = ExtractionModel.objects.filter(assigned_to_id=user_id)

        if include_quotes:
            qs = qs.prefetch_related('quotes__tags')

        return [ExtractionMapper.to_domain(m) for m in qs]