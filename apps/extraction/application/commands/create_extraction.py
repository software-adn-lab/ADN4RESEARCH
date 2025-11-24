from dataclasses import dataclass
from django.db import transaction

from ...domain.repositories.i_extraction_phase_repository import IExtractionPhaseRepository
from ...domain.repositories.i_extraction_repository import IExtractionRepository
from ...domain.entities.extraction import Extraction
from ...domain.value_objects.extraction_status import ExtractionStatus
from ...domain.exceptions.extraction_exceptions import StudyNotFound, ExtractionValidationError


@dataclass
class CreateExtractionCommand:
    study_id: int
    user_id: int
    project_id: int


class CreateExtractionHandler:
    def __init__(self, repository: IExtractionRepository, study_adapter, phase_repo: IExtractionPhaseRepository):
        self.repository = repository
        self.study_adapter = study_adapter
        self.phase_repo = phase_repo

    @transaction.atomic
    def handle(self, command: CreateExtractionCommand) -> Extraction:
        if not self.study_adapter.exists(command.study_id):
            raise StudyNotFound(
                f"El estudio {command.study_id} no existe"
            )

        phase = self.phase_repo.get_by_project_id(command.project_id)
        if not phase:
            raise ExtractionValidationError(
                "La fase de extracción no está configurada para este proyecto"
            )

        if not phase.is_open_for_extraction():
            raise ExtractionValidationError(
                "La fase de extracción no está activa o ya cerró"
            )

        existing_extractions = self.repository.get_all_by_study_id(command.study_id)
        current_count = len(existing_extractions)

        phase.validate_extraction_count(command.study_id, current_count)

        user_extraction = self.repository.get_by_study_and_user(
            command.study_id,
            command.user_id
        )

        if user_extraction:
            raise ExtractionValidationError(
                "Ya tienes una extracción asignada para este estudio"
            )

        extraction_order = current_count + 1

        new_extraction = Extraction(
            id=None,
            study_id=command.study_id,
            assigned_to_user_id=command.user_id,
            status=ExtractionStatus.PENDING,
            extraction_order=extraction_order,
            max_quotes=phase.max_quotes_per_extraction
        )

        saved_extraction = self.repository.save(new_extraction)
        return saved_extraction