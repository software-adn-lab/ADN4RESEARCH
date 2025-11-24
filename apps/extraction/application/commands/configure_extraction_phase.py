from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from django.db import transaction

from ...domain.entities.extraction_phase import ExtractionPhase
from ...domain.repositories.i_extraction_phase_repository import IExtractionPhaseRepository
from ...domain.repositories.i_project_repository import IProjectRepository
from ...domain.value_objects.extraction_mode import ExtractionMode
from ...domain.value_objects.phase_status import PhaseStatus
from ...domain.exceptions.extraction_exceptions import (
    ProjectAccessDenied,
    ExtractionValidationError
)


@dataclass
class ConfigureExtractionPhaseCommand:
    project_id: int
    user_id: int
    mode: str  # 'Single', 'Double', 'Triple'
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    auto_close: bool = False
    allow_late_submissions: bool = False
    min_quotes_required: int = 1
    max_quotes_per_extraction: int = 100
    requires_approval: bool = False


class ConfigureExtractionPhaseHandler:
    def __init__(
            self,
            phase_repo: IExtractionPhaseRepository,
            project_repo: IProjectRepository
    ):
        self.phase_repo = phase_repo
        self.project_repo = project_repo

    @transaction.atomic
    def handle(self, command: ConfigureExtractionPhaseCommand) -> ExtractionPhase:
        project = self.project_repo.get_project_by_id(command.project_id)
        if not project or project.owner_id != command.user_id:
            raise ProjectAccessDenied(
                "Solo el owner del proyecto puede configurar la fase de extracción"
            )

        phase = self.phase_repo.get_by_project_id(command.project_id)

        if phase:
            if not phase.can_be_modified():
                raise ExtractionValidationError(
                    "No se puede modificar una fase activa o cerrada. "
                    "Primero debes pausarla o completarla."
                )

            phase.mode = ExtractionMode(command.mode)
            phase.start_date = command.start_date
            phase.end_date = command.end_date
            phase.auto_close = command.auto_close
            phase.allow_late_submissions = command.allow_late_submissions
            phase.min_quotes_required = command.min_quotes_required
            phase.max_quotes_per_extraction = command.max_quotes_per_extraction
            phase.requires_approval = command.requires_approval
        else:
            phase = ExtractionPhase(
                id=None,
                project_id=command.project_id,
                mode=ExtractionMode(command.mode),
                status=PhaseStatus.INACTIVE,
                start_date=command.start_date,
                end_date=command.end_date,
                auto_close=command.auto_close,
                allow_late_submissions=command.allow_late_submissions,
                min_quotes_required=command.min_quotes_required,
                max_quotes_per_extraction=command.max_quotes_per_extraction,
                requires_approval=command.requires_approval
            )

        if command.end_date and command.start_date:
            if command.end_date <= command.start_date:
                raise ExtractionValidationError(
                    "La fecha de fin debe ser posterior a la fecha de inicio"
                )

        if command.min_quotes_required > command.max_quotes_per_extraction:
            raise ExtractionValidationError(
                "El mínimo de quotes no puede ser mayor al máximo"
            )

        return self.phase_repo.save(phase)