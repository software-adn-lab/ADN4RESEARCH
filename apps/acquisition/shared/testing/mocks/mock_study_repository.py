from typing import Dict, List, Optional
from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.shared.domain.repositories.i_study_repository import IStudyRepository
from apps.acquisition.shared.domain.value_objects.study_status import StudyStatus

class MockStudyRepository(IStudyRepository):
    """
    Mock en memoria del repositorio de estudios.
    """
    def __init__(self):
        self._studies: Dict[str, Study] = {}
    
    def save(self, study: Study) -> Study:
        self._studies[study.id] = study
        return study
    
    def save_batch(self, studies: List[Study]) -> List[Study]:
        for study in studies:
            self.save(study)
        return studies
    
    def find_by_id(self, study_id: str) -> Optional[Study]:
        return self._studies.get(study_id)
    
    def find_by_doi(self, doi: str) -> Optional[Study]:
        for study in self._studies.values():
            if study.doi and study.doi.value == doi:
                return study
        return None
    
    def find_by_title_and_source(self, title: str, source: str) -> Optional[Study]:
        for study in self._studies.values():
            if study.title == title and study.source.name == source:
                return study
        return None
    
    def find_all_by_status(self, status: StudyStatus) -> List[Study]:
        return [s for s in self._studies.values() if s.status == status]
    
    def find_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Study]:
        studies = list(self._studies.values())
        if offset:
            studies = studies[offset:]
        if limit:
            studies = studies[:limit]
        return studies
    
    def count_by_status(self, status: StudyStatus) -> int:
        return len(self.find_all_by_status(status))
    
    def delete(self, study_id: str) -> bool:
        if study_id in self._studies:
            del self._studies[study_id]
            return True
        return False
    
    def exists_by_doi(self, doi: str) -> bool:
        return self.find_by_doi(doi) is not None
    
    def exists_by_title_and_source(self, title: str, source: str) -> bool:
        return self.find_by_title_and_source(title, source) is not None
