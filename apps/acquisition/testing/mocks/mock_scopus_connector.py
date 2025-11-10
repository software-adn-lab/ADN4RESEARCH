"""
Mock Scopus connector for testing.
"""
from typing import List, Union

from apps.acquisition.domain.interfaces.i_academic_connector import IAcademicConnector
from apps.acquisition.domain.entities.study import Study


class MockScopusConnector(IAcademicConnector):
    """
    Mock implementation of Scopus connector for testing purposes.
    """

    def search(self, query: str, max_results: int = 10) -> List[Union[dict, Study]]:
        """
        Mock search implementation.

        Args:
            query: The search query
            max_results: Maximum number of results to return

        Returns:
            Empty list (stub implementation)
        """
        return []
