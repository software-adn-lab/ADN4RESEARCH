from dataclasses import dataclass

from django.db import transaction

from apps.extraction.domain.exceptions.extraction_exceptions import ExtractionValidationError, \
    UnauthorizedExtractionAccess
from apps.extraction.domain.repositories.i_project_repository import IProjectRepository
from apps.extraction.domain.value_objects.tag_status import TagStatus


@dataclass
class MergeTagsCommand:
    target_tag_id: int  # El que queda (ej: "Costo oculto")
    source_tag_id: int  # El que desaparece (ej: "Costos oc.")
    user_id: int


class MergeTagsHandler:
    def __init__(
        self,
        tag_repo,
        merge_service,
        project_repo: IProjectRepository
    ):
        self.tag_repo = tag_repo
        self.merge_service = merge_service
        self.project_repo = project_repo

    @transaction.atomic
    def handle(self, command):
        target = self.tag_repo.get_by_id(command.target_tag_id)
        source = self.tag_repo.get_by_id(command.source_tag_id)

        if target.project_id != source.project_id:
            raise ExtractionValidationError(
                "Solo se pueden fusionar tags del mismo proyecto"
            )

        project = self.project_repo.get_project_by_id(target.project_id)
        if not project or project.owner_id != command.user_id:
            raise UnauthorizedExtractionAccess(
                "Solo el owner del proyecto puede fusionar tags"
            )

        if target.status != TagStatus.APPROVED or source.status != TagStatus.APPROVED:
            raise ExtractionValidationError(
                "Solo se pueden fusionar tags aprobados"
            )

        if source.is_mandatory:
            raise ExtractionValidationError(
                "No se puede fusionar un tag obligatorio"
            )

        self.merge_service.merge_tags(target, source)