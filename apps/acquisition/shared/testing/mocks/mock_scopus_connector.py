"""
Mock Scopus connector for testing.
"""
from typing import List, Dict, Optional

from apps.acquisition.discovery.domain.interfaces.i_academic_connector import IAcademicConnector
from apps.acquisition.shared.domain.entities.study import Study


class MockScopusConnector(IAcademicConnector):
    """Mock implementation of Scopus connector for testing purposes."""

    def search(self, query: str, max_results: int = 10) -> List[Study]:
        """Mock search implementation with deterministic fixtures."""
        return [
            Study.create_discovered(
                title="Neural Networks for Fault Detection in Code",
                link="https://scopus.example.com/study1",
                source="Scopus",
                doi="10.1109/tse.2023.shared"
            ),
            Study.create_discovered(
                title="Machine-Learning: A Survey",
                link="https://scopus.example.com/study2",
                source="Scopus",
                doi=None
            ),
            Study.create_discovered(
                title="Software Quality Assessment using AI",
                link="https://scopus.example.com/study3",
                source="Scopus",
                doi="10.1016/j.tse.2023.unique"
            ),
        ]

    def find_metadata(self, title: str) -> Optional[Dict[str, str]]:
        """Mock metadata search for consolidation."""
        if "Deep Learning" in title or "Software Testing" in title:
            return {
                "doi": "10.1016/j.future.2020.001",
                "abstract": "Abstract recovered by automatic enrichment from Scopus API."
            }
        return None
