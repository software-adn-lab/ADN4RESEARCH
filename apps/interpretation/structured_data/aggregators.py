from dataclasses import dataclass
from typing import List, Optional, Dict, Any

# Django Imports
from apps.acquisition.models import StudyModel
from apps.design.research_question.models.research_question import ResearchQuestion
from apps.design.search_strategy.models.search_strategy import SearchStrategy
from apps.acquisition.models import SearchExecutionModel
from apps.extraction.core.models import PaperExtraction


@dataclass
class UnifiedStudyDTO:
    """
    Data Transfer Object representing a unified view of a study
    for interpretation purposes.
    """

    study_id: str
    title: str
    year: Optional[int]
    authors: List[str]
    source: str
    doi: Optional[str]
    abstract: Optional[str]
    # Placeholder for extracted data
    extracted_data: Dict[str, Any] | None = None


class DataAggregator:
    """
    Responsible for fetching and aggregating data from Acquisition and Extraction modules.
    """

    def get_unified_studies(self, project_id: str) -> List[UnifiedStudyDTO]:
        """
        Fetches studies associated with a project through the Design -> Acquisition chain.
        Also attempts to attach extraction data if available.
        """
        # 1. Identify relevant Search Strategies for the Project
        # Project -> DesignPhase -> ResearchQuestion -> SearchStrategy
        try:
            p_id = int(project_id)
        except ValueError:
            return []

        rqs = ResearchQuestion.objects.filter(design_phase_id=p_id)
        strategies = SearchStrategy.objects.filter(research_question__in=rqs)

        # 2. Identify Executions
        executions = SearchExecutionModel.objects.filter(strategy__in=strategies)

        # 3. Fetch Studies
        # We use distinct() to avoid duplicates if a study was found in multiple executions
        studies_qs = StudyModel.objects.filter(executions__in=executions).distinct()

        # 4. Fetch Extractions (Best Effort)
        # Note: There is currently a type mismatch between StudyModel.uuid (UUID)
        # and PaperExtraction.study_id (Integer).
        # We fetch extractions by project_id and will try to map if possible,
        # or leave extracted_data empty for now until the ID schema is unified.
        extractions = PaperExtraction.objects.filter(project_id=project_id).prefetch_related('quotes__tags')
        extraction_map = {str(e.study_id): e for e in extractions}

        unified_studies = []
        for study in studies_qs:
            # Map StudyModel to DTO
            dto = UnifiedStudyDTO(
                study_id=str(study.uuid),
                title=study.title,
                year=study.year,
                authors=study.authors if study.authors else [],
                source=study.source,
                doi=study.doi,
                abstract=study.abstract,
                extracted_data=None,  # Default
            )

            # Attempt to link extraction data
            # Assuming for now that if study_id in extraction matches the string representation of UUID
            # (which is unlikely given it's an IntegerField, but we handle the logic structure)
            # If PaperExtraction.study_id is indeed an integer, we can't link it to UUID here.
            # This part is a placeholder for when the ID schema is fixed.
            if str(study.uuid) in extraction_map:
                extraction = extraction_map[str(study.uuid)]
                dto.extracted_data = {
                    "status": extraction.status,
                    "quotes": [
                        {
                            "text": quote.text_portion,
                            "location": quote.location,
                            "tags": [tag.name for tag in quote.tags.all()]
                        }
                        for quote in extraction.quotes.all()
                    ]
                }

            unified_studies.append(dto)

        return unified_studies
