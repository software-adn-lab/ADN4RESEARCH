"""
Mock Scopus connector for testing.

FIXTURES DETERMINISTAS FASE 1:
- 1 estudio con DOI compartido con IEEE (duplicado por DOI)
- 1 estudio con título equivalente al de IEEE bajo normalización (duplicado por título, sin DOI)
- 1 estudio único de Scopus
- Total: 3 estudios (1 duplicado DOI + 1 duplicado título + 1 único)
"""
from typing import List

from apps.acquisition.domain.interfaces.i_academic_connector import IAcademicConnector
from apps.acquisition.domain.entities.study import Study


class MockScopusConnector(IAcademicConnector):
    """
    Mock implementation of Scopus connector for testing purposes.

    Fixtures deterministas que fuerzan comportamiento clave:
    1. Deduplicación por DOI (mismo DOI que IEEE)
    2. Deduplicación por título normalizado (variantes de título sin DOI)
    3. Validación de estructura mínima (title, link, source)
    """

    def search(self, query: str, max_results: int = 10) -> List[Study]:
        """
        Mock search implementation with deterministic fixtures.

        Args:
            query: The search query (not used in mock)
            max_results: Maximum number of results to return

        Returns:
            List of 3 Study objects:
            - 1 duplicado con IEEE por DOI
            - 1 duplicado con IEEE por título normalizado (sin DOI)
            - 1 único de Scopus
        """
        return [
            # CASO 1: Duplicado por DOI (mismo DOI que IEEE)
            Study(
                title="Neural Networks for Fault Detection in Code",
                link="https://scopus.example.com/study1",
                source="Scopus",
                doi="10.1109/tse.2023.shared"  # ← Mismo DOI que IEEE
            ),

            # CASO 2: Duplicado por título normalizado (sin DOI)
            # Título con variaciones: mayúsculas, guiones, puntuación
            # Debe coincidir con IEEE bajo normalización
            Study(
                title="Machine-Learning: A Survey",  # ← Variante con guión y mayúsculas
                link="https://scopus.example.com/study2",
                source="Scopus",
                doi=None  # ← Sin DOI para forzar deduplicación por título
            ),

            # CASO 3: Estudio único de Scopus
            Study(
                title="Software Quality Assessment using AI",
                link="https://scopus.example.com/study3",
                source="Scopus",
                doi="10.1016/j.tse.2023.unique"
            ),
        ]
