# apps/extraction/application/queries/list_extractions.py

from dataclasses import dataclass
from typing import List, Optional
from ...domain.repositories.i_extraction_repository import IExtractionRepository
from ...domain.entities.extraction import Extraction


@dataclass
class ListExtractionsQuery:
    user_id: Optional[int] = None
    study_id: Optional[int] = None
    include_quotes: bool = False


class ListExtractionsHandler:
    def __init__(self, repository: IExtractionRepository):
        self.repository = repository

    def handle(self, query: ListExtractionsQuery) -> List[Extraction]:
        if query.user_id:
            return self.repository.list_by_user(
                query.user_id,
                include_quotes=query.include_quotes
            )
        return []