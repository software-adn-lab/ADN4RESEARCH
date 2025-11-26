from abc import ABC, abstractmethod
from typing import Any, Optional


class IAcquisitionRepository(ABC):
    """
    Puerto para comunicarse con el Bounded Context de 'Studies' (o Papers).
    Retorna un DTO o Dict genérico, ya que 'Study' no es una entidad de ESTE dominio.
    """

    @abstractmethod
    def get_study_details(self, study_id: int) -> dict:
        pass

    @abstractmethod
    def exists(self, study_id: int) -> bool:
        pass

    @abstractmethod
    def get_project_context(self, study_id: int) -> Optional[int]:
        pass