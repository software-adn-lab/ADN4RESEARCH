from typing import Dict

from .dtos import CompletionResult
from .models import PaperExtraction, PaperExtractionStatusChoices

class PaperLifecycleService:
    """
    Servicio para manejar el ciclo de vida de un paper individual.
    """

    def mark_paper_as_complete(self, extraction_id: int) -> CompletionResult:
        """
        Intenta completar el paper. Retorna un objeto CompletionResult tipado.
        """
        paper = PaperExtraction.objects.get(id=extraction_id)

        missing_tags = paper.get_missing_mandatory_tags()

        if missing_tags.exists():
            return CompletionResult(
                success=False,
                paper=paper,
                errors=[tag.name for tag in missing_tags]
            )
        paper.status = PaperExtractionStatusChoices.COMPLETED
        paper.save()

        return CompletionResult(
            success=True,
            paper=paper
        )