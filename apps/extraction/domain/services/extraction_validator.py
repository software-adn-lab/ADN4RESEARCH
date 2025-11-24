from typing import List
from ..entities.extraction import Extraction
from ..repositories.i_tag_repository import ITagRepository


class ExtractionValidator:
    def __init__(self, tag_repository: ITagRepository):
        self.tag_repository = tag_repository

    def validate_completeness(self, extraction: Extraction) -> List[str]:
        """
        Verifica qué tags obligatorios faltan en la extracción.
        Retorna una lista de nombres de tags faltantes.
        """
        mandatory_tags = self.tag_repository.get_mandatory_tags_for_project_context(extraction.study_id)

        # Obtener IDs de tags usados en las quotes de esta extracción
        used_tag_ids = {tag.id for quote in extraction.quotes for tag in quote.tags}

        missing_tags = []
        for mandatory in mandatory_tags:
            if mandatory.id not in used_tag_ids:
                missing_tags.append(mandatory.name)

        return missing_tags