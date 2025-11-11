"""
Mock IEEE connector for testing.

FIXTURES DETERMINISTAS:
- 2 estudios únicos de IEEE
- 1 estudio duplicado con Scopus (mismo DOI: 10.1109/tse.2023.shared)
- Total: 3 estudios (2 únicos + 1 duplicado)
"""
from typing import List

from apps.acquisition.domain.interfaces.i_academic_connector import IAcademicConnector
from apps.acquisition.domain.entities.study import Study


class MockIeeeConnector(IAcademicConnector):
    """
    Mock implementation of IEEE connector for testing purposes.

    Retorna fixtures deterministas para pruebas de:
    - Deduplicación (incluye 1 duplicado con Scopus por DOI)
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
            List of 3 Study objects (2 unique + 1 duplicate with Scopus)
        """
        # Fixture: 3 estudios de IEEE
        # - study_ieee_1, study_ieee_2: únicos
        # - study_ieee_3: duplicado con Scopus (mismo DOI)
        return [
            Study(
                title="Automated Testing with Machine Learning",
                link="https://ieeexplore.ieee.org/document/12345",
                source="IEEE Xplore",
                doi="10.1109/icse.2023.001"
            ),
            Study(
                title="Code Review Automation using Deep Learning",
                link="https://ieeexplore.ieee.org/document/12346",
                source="IEEE Xplore",
                doi="10.1109/ase.2023.002"
            ),
            Study(
                title="Neural Networks for Fault Detection in Code",  # ← Mismo título que Scopus
                link="https://ieeexplore.ieee.org/document/12347",
                source="IEEE Xplore",
                doi="10.1109/tse.2023.shared"  # ← Mismo DOI que Scopus study_4
            ),
        ]
