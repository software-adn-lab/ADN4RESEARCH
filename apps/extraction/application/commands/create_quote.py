from dataclasses import dataclass
from typing import List, Optional
from django.db import transaction
from ...domain.entities.quote import Quote
from ...domain.repositories.i_extraction_repository import IExtractionRepository
from ...domain.repositories.i_quote_repository import IQuoteRepository
from ...domain.repositories.i_tag_repository import ITagRepository
from ...domain.repositories.i_acquisition_repository import IAcquisitionRepository
from ...domain.value_objects.quote_location import QuoteLocation
from ...domain.value_objects.tag_status import TagStatus
from ...domain.exceptions.extraction_exceptions import (
    ExtractionNotFound,
    UnauthorizedExtractionAccess,
    InvalidExtractionState,
    TagNotFound,
    ExtractionValidationError
)


@dataclass
class CreateQuoteCommand:
    extraction_id: int
    text: str
    user_id: int
    tag_ids: List[int]

    page: int
    text_location: str = ""
    x1: Optional[float] = None
    y1: Optional[float] = None
    x2: Optional[float] = None
    y2: Optional[float] = None


class CreateQuoteHandler:
    def __init__(
            self,
            extraction_repo: IExtractionRepository,
            quote_repo: IQuoteRepository,
            tag_repo: ITagRepository,
            acquisition_adapter: IAcquisitionRepository
    ):
        self.extraction_repo = extraction_repo
        self.quote_repo = quote_repo
        self.tag_repo = tag_repo
        self.acquisition_adapter = acquisition_adapter

    @transaction.atomic
    def handle(self, command: CreateQuoteCommand) -> Quote:
        extraction = self.extraction_repo.get_by_id(command.extraction_id)
        if not extraction:
            raise ExtractionNotFound(
                f"Extracción {command.extraction_id} no encontrada"
            )

        if extraction.assigned_to_user_id != command.user_id:
            raise UnauthorizedExtractionAccess(
                "No tienes permiso para agregar quotes a esta extracción"
            )
        if len(command.tag_ids) != len(set(command.tag_ids)):
            raise ExtractionValidationError(
                "No se pueden especificar tags duplicados"
            )

        tags = self.tag_repo.get_by_ids(command.tag_ids)
        if len(tags) != len(command.tag_ids):
            found_ids = {t.id for t in tags}
            missing = set(command.tag_ids) - found_ids
            raise TagNotFound(f"Tags no encontrados: {missing}")

        project_id = self.acquisition_adapter.get_project_context(
            extraction.study_id
        )
        if not project_id:
            raise ExtractionValidationError(
                "No se pudo determinar el proyecto de la extracción"
            )

        for tag in tags:
            if tag.project_id != project_id:
                raise ExtractionValidationError(
                    f"El tag '{tag.name}' no pertenece al proyecto actual"
                )

        for tag in tags:
            if tag.status != TagStatus.APPROVED:
                # Solo permitir tags pending si son del mismo usuario (inductivos)
                if tag.created_by_user_id != command.user_id:
                    raise ExtractionValidationError(
                        f"El tag '{tag.name}' no está aprobado para uso"
                    )

        try:
            location = QuoteLocation(
                page=command.page,
                text_location=command.text_location,
                x1=command.x1,
                y1=command.y1,
                x2=command.x2,
                y2=command.y2
            )
        except ValueError as e:
            raise ExtractionValidationError(f"Ubicación inválida: {str(e)}")

        quote = Quote(
            id=None,
            extraction_id=command.extraction_id,
            text=command.text,
            researcher_id=command.user_id,
            tags=tags,
            location=location,
        )

        extraction.add_quote(quote)

        saved_quote = self.quote_repo.save(quote)
        self.extraction_repo.save(extraction)

        return saved_quote