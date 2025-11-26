from typing import List, Optional
from ...domain.repositories.i_project_repository import IProjectRepository
from ...domain.dtos.project_dtos import ProjectDTO, ProjectMemberDTO, StageDTO

try:
    from apps.projects.services import ProjectService
except ImportError:
    ProjectService = None


class ProjectServiceAdapter(IProjectRepository):

    def __init__(self):
        self.service = ProjectService() if ProjectService else None

    def get_project_by_id(self, project_id: int) -> Optional[ProjectDTO]:
        if not self.service:
            return None

        data = self.service.get_project_details(project_id)
        if not data:
            return None

        return ProjectDTO(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            owner_id=data['owner_id']
        )

    def exists(self, project_id: int) -> bool:
        if not self.service:
            return False
        return self.service.exists(project_id)

    def is_member(self, project_id: int, user_id: int) -> bool:
        if not self.service:
            return False
        return self.service.is_member(project_id, user_id)

    def get_members(self, project_id: int) -> List[ProjectMemberDTO]:
        if not self.service:
            return []

        members = self.service.get_members(project_id)
        return [
            ProjectMemberDTO(
                user_id=m['user_id'],
                role=m['role'],
                joined_at=m['joined_at']
            )
            for m in members
        ]

    def get_current_stage(self, project_id: int) -> Optional[StageDTO]:
        if not self.service:
            return None

        data = self.service.get_current_stage(project_id)
        if not data:
            return None

        return StageDTO(
            name=data['name'],
            status=data['status']
        )