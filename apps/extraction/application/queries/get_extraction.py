from typing import Optional
from dataclasses import dataclass
from ...domain.repositories.i_extraction_repository import IExtractionRepository
from ...domain.entities.extraction import Extraction
from ...domain.exceptions.extraction_exceptions import ExtractionNotFound

@dataclass
class GetExtractionQuery:
    extraction_id: int

class GetExtractionHandler:
    def __init__(self, repository: IExtractionRepository):
        self.repository = repository

    def handle(self, query: GetExtractionQuery) -> Extraction:
        extraction = self.repository.get_by_id(query.extraction_id)
        if not extraction:
            raise ExtractionNotFound(f"Extracción {query.extraction_id} no encontrada.")
        return extraction