from typing import List
from .aggregators import UnifiedStudyDTO


class StudyFilter:
    """
    Provides filtering capabilities for the unified study dataset.
    """

    def filter_by_year(
        self, studies: List[UnifiedStudyDTO], start_year: int, end_year: int
    ) -> List[UnifiedStudyDTO]:
        return [s for s in studies if s.year and start_year <= s.year <= end_year]

    def filter_by_source(
        self, studies: List[UnifiedStudyDTO], source_name: str
    ) -> List[UnifiedStudyDTO]:
        return [
            s for s in studies if s.source and source_name.lower() in s.source.lower()
        ]

    def filter_by_keyword(
        self, studies: List[UnifiedStudyDTO], keyword: str
    ) -> List[UnifiedStudyDTO]:
        # Simple search in title or abstract
        keyword = keyword.lower()
        return [
            s
            for s in studies
            if (s.title and keyword in s.title.lower())
            or (s.abstract and keyword in s.abstract.lower())
        ]
