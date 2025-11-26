from typing import Optional, List
from .models import PaperExtraction, Quote, ExtractionStatus


class ExtractionRepository:
    """
    Repository for the PaperExtraction Aggregate.
    """

    def get_by_study_id(self, study_id: int) -> Optional[PaperExtraction]:
        try:
            return PaperExtraction.objects.select_related().get(study_id=study_id)
        except PaperExtraction.DoesNotExist:
            return None

    def get_by_id(self, extraction_id: int) -> Optional[PaperExtraction]:
        try:
            return PaperExtraction.objects.prefetch_related('quotes', 'quotes__tags').get(id=extraction_id)
        except PaperExtraction.DoesNotExist:
            return None

    def list_by_project(self, project_id: int) -> List[PaperExtraction]:
        return list(PaperExtraction.objects.filter(project_id=project_id))

    def create_extraction(self, study_id: int, project_id: int) -> PaperExtraction:
        return PaperExtraction.objects.create(
            study_id=study_id,
            project_id=project_id,
            status=ExtractionStatus.PENDING
        )

    def add_quote(self, extraction: PaperExtraction, text: str, user_id: int, tags=None) -> Quote:
        quote = Quote.objects.create(
            paper_extraction=extraction,
            text_portion=text,
            researcher_id=user_id
        )
        if tags:
            quote.tags.set(tags)
        return quote

    def save(self, extraction: PaperExtraction) -> PaperExtraction:
        extraction.save()
        return extraction
