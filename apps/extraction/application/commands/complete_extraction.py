from dataclasses import dataclass
from ...domain.repositories.i_extraction_repository import IExtractionRepository
from ...domain.services.extraction_validator import ExtractionValidator
from ...domain.exceptions.extraction_exceptions import ExtractionValidationError


@dataclass
class CompleteExtractionCommand:
    extraction_id: int
    user_id: int


class CompleteExtractionHandler:
    def __init__(self,
                 repository: IExtractionRepository,
                 validator: ExtractionValidator):
        self.repository = repository
        self.validator = validator

    def handle(self, command: CompleteExtractionCommand):
        extraction = self.repository.get_by_id(command.extraction_id)
        if not extraction:
            raise ExtractionValidationError("Extracción no encontrada")

        if extraction.assigned_to_user_id != command.user_id:
            raise ExtractionValidationError("No tienes permiso para completar esta extracción")

        missing_tags = self.validator.validate_completeness(extraction)

        extraction.complete(missing_mandatory_tags=missing_tags)

        self.repository.save(extraction)