"""
Mock IEEE connector for testing.

FIXTURES DETERMINISTAS FASE 1:
- 1 estudio con DOI compartido con Scopus (duplicado por DOI)
- 1 estudio con título equivalente al de Scopus bajo normalización (duplicado por título, sin DOI)
- 1 estudio único de IEEE
- Total: 3 estudios (1 duplicado DOI + 1 duplicado título + 1 único)
"""
from typing import List

from apps.acquisition.discovery.domain.interfaces.i_academic_connector import IAcademicConnector
from apps.acquisition.shared.domain.entities.study import Study


class MockIeeeConnector(IAcademicConnector):
    """
    Mock implementation of IEEE connector for testing purposes.

    Fixtures deterministas que fuerzan comportamiento clave:
    1. Deduplicación por DOI (mismo DOI que Scopus)
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
            - 1 duplicado con Scopus por DOI
            - 1 duplicado con Scopus por título normalizado (sin DOI)
            - 1 único de IEEE
        """
        return [
            # CASO 1: Duplicado por DOI (mismo DOI que Scopus)
            Study.create_discovered(
                title="Neural Networks for Fault Detection in Code",
                link="https://ieeexplore.ieee.org/document/12345",
                source="IEEE Xplore",
                doi="10.1109/tse.2023.shared"  # ← Mismo DOI que Scopus
            ),

            # CASO 2: Duplicado por título normalizado (sin DOI)
            # Título con variaciones diferentes a Scopus pero que normalizan igual
            # Scopus: "Machine-Learning: A Survey"
            # IEEE:   "MACHINE LEARNING A SURVEY!" (normaliza a lo mismo)
            Study.create_discovered(
                title="MACHINE LEARNING A SURVEY!",  # ← Variante con MAYÚSCULAS y puntuación
                link="https://ieeexplore.ieee.org/document/12346",
                source="IEEE Xplore",
                doi=None  # ← Sin DOI para forzar deduplicación por título
            ),

            # CASO 3: Estudio único de IEEE
            Study.create_discovered(
                title="Code Review Automation using Deep Learning",
                link="https://ieeexplore.ieee.org/document/12347",
                source="IEEE Xplore",
                doi="10.1109/ase.2023.unique"
            ),
        ]
