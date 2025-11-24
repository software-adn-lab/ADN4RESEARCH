from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from ..value_objects.phase_status import PhaseStatus
from ..value_objects.extraction_mode import ExtractionMode
from ..exceptions.extraction_exceptions import ExtractionValidationError


@dataclass
class ExtractionPhase:
    """
    Entidad que configura y controla la fase de extracción de un proyecto.

    Reglas de Negocio:
    - Solo puede haber una fase activa por proyecto
    - Si auto_close=True, se cierra automáticamente al alcanzar end_date
    - double_extraction requiere dos investigadores por paper
    - No se pueden modificar configuraciones con extracciones en progreso
    """

    id: Optional[int]
    project_id: int
    mode: ExtractionMode
    status: PhaseStatus
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    auto_close: bool = False
    allow_late_submissions: bool = False
    min_quotes_required: int = 1
    max_quotes_per_extraction: int = 100
    requires_approval: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def activate(self) -> None:
        """Activa la fase de extracción"""
        if self.status == PhaseStatus.ACTIVE:
            raise ExtractionValidationError("La fase ya está activa")

        if not self.start_date:
            self.start_date = datetime.now()

        self.status = PhaseStatus.ACTIVE

    def pause(self) -> None:
        """Pausa temporalmente la fase"""
        if self.status != PhaseStatus.ACTIVE:
            raise ExtractionValidationError(
                "Solo se pueden pausar fases activas"
            )
        self.status = PhaseStatus.PAUSED

    def resume(self) -> None:
        """Reanuda una fase pausada"""
        if self.status != PhaseStatus.PAUSED:
            raise ExtractionValidationError(
                "Solo se pueden reanudar fases pausadas"
            )
        self.status = PhaseStatus.ACTIVE

    def complete(self) -> None:
        """Completa manualmente la fase"""
        if self.status in [PhaseStatus.COMPLETED, PhaseStatus.AUTO_CLOSED]:
            raise ExtractionValidationError("La fase ya está cerrada")

        self.status = PhaseStatus.COMPLETED
        if not self.end_date:
            self.end_date = datetime.now()

    def auto_close_if_needed(self) -> bool:
        """
        Cierra automáticamente si cumple condiciones.
        Retorna True si se cerró.
        """
        if not self.auto_close or not self.end_date:
            return False

        if self.status != PhaseStatus.ACTIVE:
            return False

        if datetime.now() >= self.end_date:
            self.status = PhaseStatus.AUTO_CLOSED
            return True

        return False

    def is_open_for_extraction(self) -> bool:
        """Verifica si se pueden crear/modificar extracciones"""
        if self.status != PhaseStatus.ACTIVE:
            return False

        # Si hay end_date y no permite entregas tardías
        if self.end_date and not self.allow_late_submissions:
            if datetime.now() > self.end_date:
                return False

        return True

    def can_be_modified(self) -> bool:
        """Verifica si la configuración puede ser modificada"""
        # No se puede modificar si está activa o cerrada
        return self.status == PhaseStatus.INACTIVE

    def validate_extraction_count(self, study_id: int, current_count: int) -> None:
        """
        Valida si se puede crear otra extracción para un estudio.

        Args:
            study_id: ID del estudio
            current_count: Número de extracciones existentes para ese estudio
        """
        if self.mode == ExtractionMode.SINGLE and current_count >= 1:
            raise ExtractionValidationError(
                "Ya existe una extracción para este estudio (modo: extracción simple)"
            )

        if self.mode == ExtractionMode.DOUBLE and current_count >= 2:
            raise ExtractionValidationError(
                "Ya existen dos extracciones para este estudio (modo: extracción por pares)"
            )

        if self.mode == ExtractionMode.TRIPLE and current_count >= 3:
            raise ExtractionValidationError(
                "Ya existen tres extracciones para este estudio (modo: triple validación)"
            )

    @property
    def requires_multiple_extractors(self) -> bool:
        """Indica si requiere múltiples extractores"""
        return self.mode in [ExtractionMode.DOUBLE, ExtractionMode.TRIPLE]

    @property
    def expected_extractions_per_study(self) -> int:
        """Número esperado de extracciones por estudio"""
        mode_map = {
            ExtractionMode.SINGLE: 1,
            ExtractionMode.DOUBLE: 2,
            ExtractionMode.TRIPLE: 3,
        }
        return mode_map.get(self.mode, 1)