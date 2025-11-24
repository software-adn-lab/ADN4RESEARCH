from typing import Optional
from ...domain.repositories.i_acquisition_repository import IAcquisitionRepository

try:
    from apps.acquisition.services import AcquisitionService
except ImportError:
    AcquisitionService = None


class AcquisitionServiceAdapter(IAcquisitionRepository):

    def __init__(self):
        self.service = AcquisitionService() if AcquisitionService else None

    def get_study_details(self, study_id: int) -> dict:
        if not self.service:
            return {}
        return self.service.get_study_details(study_id) or {}

    def exists(self, study_id: int) -> bool:
        if not self.service:
            return False
        return self.service.exists(study_id)

    def get_project_context(self, study_id: int) -> Optional[int]:
        if not self.service:
            return None
        return self.service.get_project_id(study_id)