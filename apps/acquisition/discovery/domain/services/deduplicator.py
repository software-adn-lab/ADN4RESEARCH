"""
Deduplicator service for removing duplicate studies with intelligent merging.
"""

from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.shared.domain.normalizers import normalize_title, normalize_doi


class Deduplicator:
    """Service for deduplicating studies based on title and DOI."""

    def deduplicate(self, studies: list[Study]) -> list[Study]:
        """
        Remove duplicate studies from the list with intelligent merging.

        Args:
            studies: List of studies to deduplicate

        Returns:
            List of unique studies
        """
        if not studies:
            return []

        by_doi: dict[str, Study] = {}
        by_title: dict[str, Study] = {}
        result: list[Study] = []

        for study in studies:
            if study.doi:
                doi_key = normalize_doi(study.doi.value)
                if doi_key not in by_doi:
                    by_doi[doi_key] = study
                    result.append(study)
            else:
                title_key = normalize_title(study.title)
                if title_key not in by_title:
                    by_title[title_key] = study
                    result.append(study)

        for title_key, study_without_doi in list(by_title.items()):
            for study_with_doi in by_doi.values():
                if normalize_title(study_with_doi.title) == title_key:
                    from apps.acquisition.shared.domain.value_objects import DOI
                    study_without_doi.doi = DOI(study_with_doi.doi.value)

                    if study_without_doi in result:
                        result.remove(study_without_doi)

                    break

        return result
