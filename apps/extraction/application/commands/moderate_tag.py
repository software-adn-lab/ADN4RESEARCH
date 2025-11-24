from dataclasses import dataclass

from django.db import transaction

from apps.extraction.domain.exceptions.extraction_exceptions import UnauthorizedExtractionAccess
from apps.extraction.domain.repositories.i_project_repository import IProjectRepository
from apps.extraction.domain.repositories.i_tag_repository import ITagRepository


@dataclass
class ModerateTagCommand:
    tag_id: int
    action: str  # 'APPROVE' or 'REJECT'
    owner_id: int  # Para validar que quien modera tiene permisos


class ModerateTagHandler:
    def __init__(self, tag_repo: ITagRepository, project_repo: IProjectRepository):
        self.tag_repo = tag_repo
        self.project_repo = project_repo

    @transaction.atomic
    def handle(self, command):
        tag = self.tag_repo.get_by_id(command.tag_id)
        project = self.project_repo.get_project_by_id(tag.project_id)
        if not project or project.owner_id != command.owner_id:
            raise UnauthorizedExtractionAccess(
                "Solo el owner del proyecto puede moderar tags"
            )

        if command.action == 'APPROVE':
            tag.approve()
        elif command.action == 'REJECT':
            tag.reject()

        self.tag_repo.save(tag)