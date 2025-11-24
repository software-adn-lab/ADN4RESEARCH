from dataclasses import dataclass
from typing import Optional
from django.db import transaction

from ...domain.entities.tag import Tag
from ...domain.repositories.i_design_repository import IDesignRepository
from ...domain.repositories.i_project_repository import IProjectRepository
from ...domain.value_objects.tag_type import TagType
from ...domain.value_objects.tag_status import TagStatus
from ...domain.value_objects.tag_visibility import TagVisibility
from ...domain.repositories.i_tag_repository import ITagRepository
from ...domain.exceptions.extraction_exceptions import (
    ProjectAccessDenied,
    ExtractionValidationError
)


@dataclass
class CreateTagCommand:
    name: str
    user_id: int
    project_id: int
    is_inductive: bool
    question_id: Optional[int] = None


class CreateTagHandler:
    def __init__(
            self,
            tag_repo: ITagRepository,
            design_repo: IDesignRepository,
            project_repo: IProjectRepository
    ):
        self.tag_repo = tag_repo
        self.design_repo = design_repo
        self.project_repo = project_repo

    @transaction.atomic
    def handle(self, command: CreateTagCommand) -> Tag:
        if not self.project_repo.is_member(command.project_id, command.user_id):
            raise ProjectAccessDenied(
                f"El usuario {command.user_id} no pertenece al proyecto {command.project_id}"
            )

        if not self.project_repo.exists(command.project_id):
            raise ExtractionValidationError(
                f"El proyecto {command.project_id} no existe"
            )

        if command.question_id:
            if not self.design_repo.question_exists(command.question_id):
                raise ExtractionValidationError(
                    f"La pregunta de investigación {command.question_id} no existe"
                )

            question_dto = self.design_repo.get_question_by_id(command.question_id)
            if question_dto.project_id != command.project_id:
                raise ExtractionValidationError(
                    "La pregunta no pertenece al proyecto indicado"
                )

        status = TagStatus.PENDING if command.is_inductive else TagStatus.APPROVED
        visibility = TagVisibility.PRIVATE if command.is_inductive else TagVisibility.PUBLIC
        type_ = TagType.INDUCTIVE if command.is_inductive else TagType.DEDUCTIVE

        tag = Tag(
            id=None,
            name=command.name,
            project_id=command.project_id,
            is_mandatory=False,
            created_by_user_id=command.user_id,
            question_id=command.question_id,
            status=status,
            visibility=visibility,
            type=type_
        )

        return self.tag_repo.save(tag)