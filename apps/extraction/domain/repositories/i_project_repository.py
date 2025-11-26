from abc import ABC, abstractmethod
from typing import List, Optional
from ..dtos.project_dtos import ProjectDTO, ProjectMemberDTO, StageDTO

class IProjectRepository(ABC):
    """
    Puerto para comunicarse con el Bounded Context de 'Projects'.
    """

    @abstractmethod
    def get_project_by_id(self, project_id: int) -> Optional[ProjectDTO]:
        pass

    @abstractmethod
    def exists(self, project_id: int) -> bool:
        pass

    @abstractmethod
    def is_member(self, project_id: int, user_id: int) -> bool:
        """Verifica si un usuario pertenece al equipo del proyecto."""
        pass

    @abstractmethod
    def get_members(self, project_id: int) -> List[ProjectMemberDTO]:
        """Obtiene la lista de investigadores del proyecto."""
        pass

    @abstractmethod
    def get_current_stage(self, project_id: int) -> Optional[StageDTO]:
        """
        Obtiene la etapa activa actual del proyecto.
        Útil para validar si la fase de 'Extracción' está abierta.
        """
        pass