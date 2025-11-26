from dataclasses import dataclass
from django.db import transaction

from ...domain.repositories.i_extraction_phase_repository import IExtractionPhaseRepository
from ...domain.repositories.i_project_repository import IProjectRepository
from ...domain.exceptions.extraction_exceptions import (
    ProjectAccessDenied,
    ExtractionValidationError
)


@dataclass
class ActivateExtractionPhaseCommand:
    project_id: int
    user_id: int


class ActivateExtractionPhaseHandler:
    def __init__(
            self,
            phase_repo: IExtractionPhaseRepository,
            project_repo: IProjectRepository
    ):
        self.phase_repo = phase_repo
        self.project_repo = project_repo

    @transaction.atomic
    def handle(self, command: ActivateExtractionPhaseCommand):
        project = self.project_repo.get_project_by_id(command.project_id)
        if not project or project.owner_id != command.user_id:
            raise ProjectAccessDenied(
                "Solo el owner del proyecto puede activar la fase"
            )

        phase = self.phase_repo.get_by_project_id(command.project_id)
        if not phase:
            raise ExtractionValidationError(
                "Primero debes configurar la fase de extracción"
            )

        phase.activate()

        self.phase_repo.save(phase)