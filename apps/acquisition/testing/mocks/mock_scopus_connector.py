"""
Mock Scopus connector for testing.

FIXTURES DETERMINISTAS:
- 3 estudios únicos de Scopus
- 1 estudio que será duplicado con IEEE (mismo DOI)
- Total: 4 estudios
"""
from typing import List

from apps.acquisition.domain.interfaces.i_academic_connector import IAcademicConnector
from apps.acquisition.domain.entities.study import Study


class MockScopusConnector(IAcademicConnector):
    """
    Mock implementation of Scopus connector for testing purposes.

    Retorna fixtures deterministas para pruebas de:
    - Deduplicación (incluye 1 duplicado con IEEE por DOI)
    - Validación de estructura mínima
    - Consolidación de resultados
    """

    def search(self, query: str, max_results: int = 10) -> List[Study]:
        """
        Mock search implementation with deterministic fixtures.

        Args:
            query: The search query (not used in mock)
            max_results: Maximum number of results to return

        Returns:
            List of 4 Study objects (3 unique + 1 duplicate with IEEE)
        """
        # Fixture: 4 estudios de Scopus
        # - study_scopus_1, study_scopus_2, study_scopus_3: únicos
        # - study_scopus_4: duplicado con IEEE (mismo DOI)
        return [
            Study(
                title="Machine Learning for Software Defect Prediction",
                link="https://scopus.example.com/study1",
                source="Scopus",
                doi="10.1016/j.infsof.2023.001"
            ),
            Study(
                title="Deep Learning Approaches to Bug Prediction",
                link="https://scopus.example.com/study2",
                source="Scopus",
                doi="10.1016/j.jss.2023.002"
            ),
            Study(
                title="Software Quality Assessment using AI",
                link="https://scopus.example.com/study3",
                source="Scopus",
                doi="10.1016/j.tse.2023.003"
            ),
            Study(
                title="Neural Networks for Fault Detection in Code",
                link="https://scopus.example.com/study4",
                source="Scopus",
                doi="10.1109/tse.2023.shared"  # ← Este DOI se duplica en IEEE
            ),
        ]
