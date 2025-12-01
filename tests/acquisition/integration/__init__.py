"""
Live Integration Test Suite for Acquisition Module.

This suite provides comprehensive integration testing that connects to real external services
(Scopus, IEEE, Crossref) to validate the acquisition system functionality in production-like conditions.

The suite is organized into modular test files:
- base_live_test.py: Shared configuration and utilities
- test_01_translation.py: Strategy translation testing
- test_02_discovery.py: Academic source discovery testing
- test_03_metadata_enrichment.py: Metadata enhancement testing
- test_04_downloads.py: PDF download testing
- test_05_manual_operations.py: Manual operations testing
- test_06_full_pipeline.py: End-to-end pipeline testing

All tests use the AcquisitionFacade as the primary entry point to ensure we test
the actual interface that other modules will use.
"""
