from dataclasses import dataclass
from typing import List, Dict
from ...domain.repositories.i_extraction_repository import IExtractionRepository
from ...domain.exceptions.extraction_exceptions import ExtractionNotFound


@dataclass
class GetExtractionQuotesWithLocationsQuery:
    extraction_id: int


class GetExtractionQuotesWithLocationsHandler:
    """
    Query optimizada para obtener quotes con sus ubicaciones en el PDF.

    Útil para el visor de PDF que necesita resaltar quotes.
    """

    def __init__(self, extraction_repo: IExtractionRepository):
        self.extraction_repo = extraction_repo

    def handle(self, query: GetExtractionQuotesWithLocationsQuery) -> Dict:
        extraction = self.extraction_repo.get_by_id(query.extraction_id)
        if not extraction:
            raise ExtractionNotFound(
                f"Extracción {query.extraction_id} no encontrada"
            )

        # Agrupar quotes por página
        quotes_by_page = {}
        quotes_list = []

        for quote in extraction.quotes:
            quote_data = {
                "id": quote.id,
                "text": quote.text,
                "page": quote.page_number,
                "location": quote.location.to_dict() if quote.location else None,
                "tags": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "color": t.color,
                        "is_mandatory": t.is_mandatory
                    }
                    for t in quote.tags
                ],
                "researcher_id": quote.researcher_id
            }

            quotes_list.append(quote_data)

            # Agrupar por página
            if quote.page_number:
                if quote.page_number not in quotes_by_page:
                    quotes_by_page[quote.page_number] = []
                quotes_by_page[quote.page_number].append(quote_data)

        return {
            "extraction_id": extraction.id,
            "study_id": extraction.study_id,
            "total_quotes": len(quotes_list),
            "quotes": quotes_list,
            "quotes_by_page": quotes_by_page
        }