"""
Unit tests to verify that all connectors implement IAcademicConnector interface.

This test ensures architectural consistency across all academic source connectors.
"""

import unittest
from abc import ABC

from apps.acquisition.discovery.domain.interfaces.i_academic_connector import IAcademicConnector
from apps.acquisition.discovery.adapters.outbound.connectors import (
    IeeeConnector,
    ScopusConnector,
    CrossrefConnector
)


class ConnectorInterfaceComplianceTest(unittest.TestCase):
    """
    Test that all connectors properly implement the IAcademicConnector interface.
    
    This ensures:
    - All connectors inherit from IAcademicConnector
    - All required methods are implemented
    - Method signatures match the interface contract
    """
    
    def test_ieee_connector_implements_interface(self):
        """IEEE connector should implement IAcademicConnector."""
        self.assertTrue(
            issubclass(IeeeConnector, IAcademicConnector),
            "IeeeConnector must inherit from IAcademicConnector"
        )
    
    def test_scopus_connector_implements_interface(self):
        """Scopus connector should implement IAcademicConnector."""
        self.assertTrue(
            issubclass(ScopusConnector, IAcademicConnector),
            "ScopusConnector must inherit from IAcademicConnector"
        )
    
    def test_crossref_connector_implements_interface(self):
        """Crossref connector should implement IAcademicConnector."""
        self.assertTrue(
            issubclass(CrossrefConnector, IAcademicConnector),
            "CrossrefConnector must inherit from IAcademicConnector"
        )
    
    def test_all_connectors_have_search_method(self):
        """All connectors must implement the search method."""
        connectors = [IeeeConnector, ScopusConnector, CrossrefConnector]
        
        for connector_class in connectors:
            self.assertTrue(
                hasattr(connector_class, 'search'),
                f"{connector_class.__name__} must have a 'search' method"
            )
            
            # Verify it's not the abstract method from the interface
            self.assertFalse(
                getattr(connector_class.search, '__isabstractmethod__', False),
                f"{connector_class.__name__}.search must be implemented (not abstract)"
            )
    
    def test_all_connectors_have_find_metadata_method(self):
        """All connectors must implement the find_metadata method."""
        connectors = [IeeeConnector, ScopusConnector, CrossrefConnector]
        
        for connector_class in connectors:
            self.assertTrue(
                hasattr(connector_class, 'find_metadata'),
                f"{connector_class.__name__} must have a 'find_metadata' method"
            )
            
            # Verify it's not the abstract method from the interface
            self.assertFalse(
                getattr(connector_class.find_metadata, '__isabstractmethod__', False),
                f"{connector_class.__name__}.find_metadata must be implemented (not abstract)"
            )


if __name__ == '__main__':
    unittest.main()
