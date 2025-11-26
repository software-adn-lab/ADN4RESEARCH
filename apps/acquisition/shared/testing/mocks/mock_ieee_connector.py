"""
Mock IEEE connector for testing.
"""
from typing import List, Dict, Optional

from apps.acquisition.discovery.domain.interfaces.i_academic_connector import IAcademicConnector
from apps.acquisition.shared.domain.entities.study import Study


class MockIeeeConnector(IAcademicConnector):
    """Mock implementation of IEEE connector for testing purposes."""

    def search(self, query: str, max_results: int = 10) -> List[Study]:
        """Mock search implementation with deterministic fixtures."""
        return [
            Study.create_discovered(
                title="Neural Networks for Fault Detection in Code",
                link="https://ieeexplore.ieee.org/document/12345",
                source="IEEE Xplore",
                doi="10.1109/tse.2023.shared"
            ),
            Study.create_discovered(
                title="MACHINE LEARNING A SURVEY!",
                link="https://ieeexplore.ieee.org/document/12346",
                source="IEEE Xplore",
                doi=None
            ),
            Study.create_discovered(
                title="Code Review Automation using Deep Learning",
                link="https://ieeexplore.ieee.org/document/12347",
                source="IEEE Xplore",
                doi="10.1109/ase.2023.unique"
            ),
        ]

    def find_metadata(self, title: str) -> Optional[Dict[str, str]]:
        """Mock metadata search for consolidation."""
        return None
