from typing import List, Optional
from .aggregators import DataAggregator, UnifiedStudyDTO
from .filters import StudyFilter


class StructuredDataManager:
    """
    Facade for the Structured Data Manager component.
    Orchestrates data aggregation and filtering.
    """

    def __init__(self):
        self.aggregator = DataAggregator()
        self.filter_engine = StudyFilter()

    def get_studies_for_interpretation(
        self, project_id: str, filters: Optional[dict] = None
    ) -> List[UnifiedStudyDTO]:
        """
        Retrieves a list of studies, optionally filtered.
        """
        studies = self.aggregator.get_unified_studies(project_id)

        if filters:
            if "year_start" in filters and "year_end" in filters:
                studies = self.filter_engine.filter_by_year(
                    studies, filters["year_start"], filters["year_end"]
                )
            if "source" in filters:
                studies = self.filter_engine.filter_by_source(
                    studies, filters["source"]
                )
            if "keyword" in filters:
                studies = self.filter_engine.filter_by_keyword(
                    studies, filters["keyword"]
                )

        return studies
