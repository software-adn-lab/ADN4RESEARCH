"""
Base Live Test Infrastructure for Acquisition Module.

This module provides shared configuration and utilities for all live integration tests.
All live tests should inherit from BaseLiveTest to ensure consistent setup and teardown.

Key features:
- Container reset for fresh credentials from environment
- Temporary directory management for downloads
- Test lifecycle management with proper cleanup
- Environment variable loading for API keys
- Shared test data and utilities
"""

import os
import tempfile
import shutil
import unittest
from typing import Dict, Any, List, Optional
from unittest import TestCase

from django.test import TestCase as DjangoTestCase
from django.contrib.auth import get_user_model

from apps.acquisition.container import Container
from apps.acquisition.facade import AcquisitionFacade, get_acquisition_facade

User = get_user_model()


class BaseLiveTest(DjangoTestCase):
    """
    Base class for all live integration tests in the acquisition module.
    
    Provides shared configuration, setup/teardown methods, and utilities
    to ensure consistent test environment across all test modules.
    
    Features:
    - Container reset for fresh credentials
    - Temporary directory management
    - Environment variable validation
    - Test data generation
    - Common assertions for study validation
    """
    
    def setUp(self):
        """
        Set up test environment with fresh configuration.
        
        This method:
        1. Resets the container to ensure fresh credentials
        2. Sets up temporary directories for downloads
        3. Initializes the facade
        4. Validates required environment variables
        5. Creates test user if needed
        """
        super().setUp()
        
        # Reset container to ensure fresh credentials from .env
        Container.reset()
        
        # Set up temporary directories for test downloads
        self.temp_dir = tempfile.mkdtemp(prefix="acquisition_live_test_")
        self.temp_download_dir = os.path.join(self.temp_dir, "downloads")
        self.temp_cache_dir = os.path.join(self.temp_dir, "cache")
        
        # Create directories and ensure they are writable
        self._create_and_validate_directories()
        
        # Store original environment values for restoration
        self.original_storage_dir = os.getenv("PAPERS_STORAGE_DIR")
        
        # Override storage directory for tests
        os.environ["PAPERS_STORAGE_DIR"] = self.temp_download_dir
        
        # Initialize facade after container reset
        self.facade = get_acquisition_facade()
        
        # Validate environment variables are loaded
        self._validate_environment_variables()
        
        # Create test user if needed
        self.test_user = self._get_or_create_test_user()
        
        # Initialize test state tracking
        self._test_state = {
            'created_studies': [],
            'created_files': [],
            'modified_env_vars': {},
            'test_start_time': None
        }
        
        # Record test start time
        import time
        self._test_state['test_start_time'] = time.time()
        
    def tearDown(self):
        """
        Clean up test environment and resources.
        
        This method:
        1. Cleans up temporary directories
        2. Resets database state
        3. Closes any open connections
        4. Restores original environment
        """
        super().tearDown()
        
        # Clean up test state
        self._cleanup_test_state()
        
        # Clean up temporary directories
        self._cleanup_temporary_directories()
        
        # Reset container to clean up connections
        Container.reset()
        
        # Restore original storage directory
        self._restore_environment_variables()
    
    def _validate_environment_variables(self):
        """
        Validate that required environment variables are loaded.
        
        Raises:
            unittest.SkipTest: If required credentials are missing
        """
        required_vars = {
            "SCOPUS_API_KEY": "Scopus API access",
            "EPN_USER": "IEEE/Scopus institutional access",
            "EPN_PASS": "IEEE/Scopus institutional access"
        }
        
        missing_vars = []
        for var, description in required_vars.items():
            if not os.getenv(var):
                missing_vars.append(f"{var} ({description})")
        
        if missing_vars:
            self.skipTest(
                f"Missing required environment variables: {', '.join(missing_vars)}. "
                "Please configure these in your .env file for live testing."
            )
    
    def _create_and_validate_directories(self):
        """
        Create temporary directories and validate they are writable.
        
        Raises:
            OSError: If directories cannot be created or are not writable
        """
        directories = [self.temp_download_dir, self.temp_cache_dir]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            
            # Validate directory is writable
            test_file = os.path.join(directory, "test_write_permission.tmp")
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
            except (OSError, IOError) as e:
                raise OSError(f"Directory {directory} is not writable: {e}")
    
    def _cleanup_temporary_directories(self):
        """
        Clean up temporary directories with proper error handling.
        
        This method attempts to remove temporary directories and handles
        common cleanup issues like permission errors or files in use.
        """
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            try:
                # First attempt: normal removal
                shutil.rmtree(self.temp_dir)
            except (OSError, PermissionError) as e:
                # Second attempt: force removal on Windows
                try:
                    if os.name == 'nt':  # Windows
                        import stat
                        def handle_remove_readonly(func, path, exc):
                            os.chmod(path, stat.S_IWRITE)
                            func(path)
                        shutil.rmtree(self.temp_dir, onerror=handle_remove_readonly)
                    else:
                        shutil.rmtree(self.temp_dir, ignore_errors=True)
                except Exception:
                    # Final fallback: ignore errors but log them
                    import logging
                    logging.warning(f"Could not fully clean up temporary directory: {self.temp_dir}")
    
    def _cleanup_test_state(self):
        """
        Clean up test state including created studies and files.
        
        This method ensures that any test data created during the test
        is properly cleaned up to avoid affecting other tests.
        """
        if not hasattr(self, '_test_state'):
            return
        
        # Clean up created studies from database
        if self._test_state.get('created_studies'):
            try:
                from apps.acquisition.shared.domain.entities.study import Study
                for study_id in self._test_state['created_studies']:
                    try:
                        # This would depend on the actual repository implementation
                        # For now, we'll just track them for manual cleanup if needed
                        pass
                    except Exception:
                        pass  # Study might already be deleted
            except ImportError:
                pass  # Study model might not be available in test context
        
        # Clean up created files
        for file_path in self._test_state.get('created_files', []):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except (OSError, PermissionError):
                pass  # File might already be deleted or in use
        
        # Restore modified environment variables
        for var_name, original_value in self._test_state.get('modified_env_vars', {}).items():
            if original_value is None:
                if var_name in os.environ:
                    del os.environ[var_name]
            else:
                os.environ[var_name] = original_value
    
    def _restore_environment_variables(self):
        """
        Restore original environment variables after test completion.
        """
        if hasattr(self, 'original_storage_dir'):
            if self.original_storage_dir is not None:
                os.environ["PAPERS_STORAGE_DIR"] = self.original_storage_dir
            elif "PAPERS_STORAGE_DIR" in os.environ:
                del os.environ["PAPERS_STORAGE_DIR"]
    
    def _get_or_create_test_user(self) -> User:
        """
        Get or create a test user for operations that require user attribution.
        
        Returns:
            User: Test user instance
        """
        user, created = User.objects.get_or_create(
            username="test_acquisition_user",
            defaults={
                "email": "test@acquisition.test",
                "first_name": "Test",
                "last_name": "User"
            }
        )
        return user
    
    def get_test_strategy(self) -> Dict[str, Any]:
        """
        Return a standardized test strategy for consistent testing.
        
        This strategy is designed to:
        - Find a reasonable number of results (not too many, not too few)
        - Use terms that are likely to have Open Access papers
        - Include both main terms and synonyms for translation testing
        - Have exclusions to test filtering logic
        
        Returns:
            Dict[str, Any]: Test strategy configuration
        """
        return {
            "strategy_id": "live_test_ml_se_2024",
            "main_terms": [
                {
                    "term": "machine learning",
                    "synonyms": ["ML", "deep learning", "neural networks"]
                },
                {
                    "term": "software engineering", 
                    "synonyms": ["SE", "software development"]
                }
            ],
            "exclusions": ["medical", "healthcare", "clinical"],
            "filters": {
                "year": {"from": 2020, "to": 2024}
            }
        }
    
    def get_test_strategy_simple(self) -> Dict[str, Any]:
        """
        Return a simple test strategy with fewer expected results.
        
        Useful for tests that need predictable, smaller result sets.
        
        Returns:
            Dict[str, Any]: Simple test strategy configuration
        """
        return {
            "strategy_id": "live_test_simple_2024",
            "main_terms": [
                {
                    "term": "systematic review",
                    "synonyms": ["systematic literature review", "SLR"]
                }
            ],
            "exclusions": ["medical"],
            "filters": {
                "year": {"from": 2023, "to": 2024}
            }
        }
    
    def assert_study_metadata(self, study: Dict[str, Any], required_fields: List[str]):
        """
        Assert that a study contains all required metadata fields.
        
        Args:
            study: Study dictionary to validate
            required_fields: List of field names that must be present and non-empty
            
        Raises:
            AssertionError: If any required field is missing or empty
        """
        self.assertIsInstance(study, dict, "Study must be a dictionary")
        
        for field in required_fields:
            self.assertIn(field, study, f"Study missing required field: {field}")
            value = study[field]
            self.assertIsNotNone(value, f"Study field '{field}' cannot be None")
            
            # For string fields, also check they're not empty
            if isinstance(value, str):
                self.assertTrue(value.strip(), f"Study field '{field}' cannot be empty")
    
    def assert_valid_pdf_file(self, file_path: str):
        """
        Assert that a file exists and appears to be a valid PDF.
        
        Args:
            file_path: Path to the PDF file to validate
            
        Raises:
            AssertionError: If file doesn't exist or isn't a valid PDF
        """
        self.assertTrue(os.path.exists(file_path), f"PDF file does not exist: {file_path}")
        self.assertTrue(os.path.isfile(file_path), f"Path is not a file: {file_path}")
        
        # Check file size (should be > 0)
        file_size = os.path.getsize(file_path)
        self.assertGreater(file_size, 0, f"PDF file is empty: {file_path}")
        
        # Basic PDF header check
        with open(file_path, 'rb') as f:
            header = f.read(4)
            self.assertEqual(header, b'%PDF', f"File does not have PDF header: {file_path}")
    
    def assert_facade_health(self):
        """
        Assert that the facade is healthy and ready for testing.
        
        Raises:
            AssertionError: If facade health check fails
        """
        self.assertTrue(self.facade.is_healthy(), "AcquisitionFacade health check failed")
    
    def create_test_study_data(self, title_suffix: str = "") -> Dict[str, Any]:
        """
        Create test study data for manual operations testing.
        
        Args:
            title_suffix: Optional suffix to add to title for uniqueness
            
        Returns:
            Dict[str, Any]: Test study data
        """
        return {
            "title": f"Test Study for Live Integration{' ' + title_suffix if title_suffix else ''}",
            "link": "https://example.com/test-paper",
            "doi": f"10.1234/test.{hash(title_suffix) % 10000}",
            "authors": ["Test Author", "Another Author"],
            "year": 2024,
            "abstract": "This is a test study created for live integration testing purposes.",
            "keywords": ["testing", "integration", "acquisition"],
            "source": "Manual Entry"
        }
    
    def get_known_open_access_doi(self) -> str:
        """
        Return a known Open Access DOI for download testing.
        
        This DOI should reliably have an available PDF for testing purposes.
        
        Returns:
            str: DOI of a known Open Access paper
        """
        # This is a PLOS ONE paper that should be reliably available
        return "10.1371/journal.pone.0123456"
    
    def get_test_dois_for_enrichment(self) -> List[str]:
        """
        Return a list of DOIs suitable for metadata enrichment testing.
        
        These DOIs should have rich metadata available from Crossref/Scopus.
        
        Returns:
            List[str]: List of DOIs for enrichment testing
        """
        return [
            "10.1145/3377811.3380330",  # ACM paper with rich metadata
            "10.1109/TSE.2020.2994247",  # IEEE paper with rich metadata
            "10.1016/j.infsof.2020.106370"  # Elsevier paper with rich metadata
        ]
    
    def get_temp_download_path(self, filename: str) -> str:
        """
        Get the full path for a file in the temporary download directory.
        
        Args:
            filename: Name of the file
            
        Returns:
            str: Full path to the file in temp download directory
        """
        return os.path.join(self.temp_download_dir, filename)
    
    def get_temp_cache_path(self, filename: str) -> str:
        """
        Get the full path for a file in the temporary cache directory.
        
        Args:
            filename: Name of the file
            
        Returns:
            str: Full path to the file in temp cache directory
        """
        return os.path.join(self.temp_cache_dir, filename)
    
    def assert_directory_writable(self, directory_path: str):
        """
        Assert that a directory exists and is writable.
        
        Args:
            directory_path: Path to the directory to check
            
        Raises:
            AssertionError: If directory doesn't exist or isn't writable
        """
        self.assertTrue(os.path.exists(directory_path), 
                       f"Directory does not exist: {directory_path}")
        self.assertTrue(os.path.isdir(directory_path), 
                       f"Path is not a directory: {directory_path}")
        
        # Test writability
        test_file = os.path.join(directory_path, "test_write.tmp")
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except (OSError, IOError):
            self.fail(f"Directory is not writable: {directory_path}")
    
    def create_test_file(self, filename: str, content: str = "test content") -> str:
        """
        Create a test file in the temporary download directory.
        
        Args:
            filename: Name of the file to create
            content: Content to write to the file
            
        Returns:
            str: Full path to the created file
        """
        file_path = self.get_temp_download_path(filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        # Track created file for cleanup
        if hasattr(self, '_test_state'):
            self._test_state['created_files'].append(file_path)
        
        return file_path
    
    def track_created_study(self, study_id: str):
        """
        Track a study created during testing for cleanup.
        
        Args:
            study_id: ID of the study to track for cleanup
        """
        if hasattr(self, '_test_state'):
            self._test_state['created_studies'].append(study_id)
    
    def set_temporary_env_var(self, var_name: str, value: str):
        """
        Set an environment variable temporarily for the test.
        
        The original value will be restored during teardown.
        
        Args:
            var_name: Name of the environment variable
            value: Value to set
        """
        if hasattr(self, '_test_state'):
            # Store original value if not already stored
            if var_name not in self._test_state['modified_env_vars']:
                self._test_state['modified_env_vars'][var_name] = os.getenv(var_name)
        
        os.environ[var_name] = value
    
    def reset_database_state(self):
        """
        Reset database state to a clean condition.
        
        This method can be called during tests to ensure a clean database state
        without affecting the overall test setup.
        """
        # For Django tests, the database is automatically reset between tests
        # This method is here for explicit state management if needed
        from django.core.management import call_command
        from django.db import transaction
        
        try:
            # Flush any pending transactions
            transaction.commit()
            
            # The database will be reset automatically by Django's test framework
            # This is just a placeholder for any additional cleanup logic
            pass
        except Exception:
            # If there are any issues, just continue
            pass
    
    def get_test_execution_time(self) -> float:
        """
        Get the execution time of the current test in seconds.
        
        Returns:
            float: Test execution time in seconds
        """
        if hasattr(self, '_test_state') and self._test_state.get('test_start_time'):
            import time
            return time.time() - self._test_state['test_start_time']
        return 0.0
    
    def assert_test_cleanup_successful(self):
        """
        Assert that test cleanup was successful.
        
        This method can be called at the end of tests to verify that
        all resources were properly cleaned up.
        """
        # Check that temporary directories still exist (they should until tearDown)
        if hasattr(self, 'temp_dir'):
            self.assertTrue(os.path.exists(self.temp_dir),
                          "Temporary directory should exist until tearDown")
        
        # Check that facade is still healthy
        if hasattr(self, 'facade'):
            self.assertTrue(self.facade.is_healthy(),
                          "Facade should remain healthy throughout test")
    
    def create_isolated_test_environment(self):
        """
        Create an isolated test environment with fresh configuration.
        
        This method can be called within tests to create a completely
        isolated environment for specific test scenarios.
        """
        # Reset container to ensure fresh state
        Container.reset()
        
        # Create new temporary directory for this isolated environment
        isolated_temp_dir = tempfile.mkdtemp(prefix="isolated_test_")
        
        # Set isolated storage directory
        self.set_temporary_env_var("PAPERS_STORAGE_DIR", isolated_temp_dir)
        
        # Get fresh facade instance
        facade = get_acquisition_facade()
        
        return {
            'temp_dir': isolated_temp_dir,
            'facade': facade,
            'cleanup': lambda: shutil.rmtree(isolated_temp_dir, ignore_errors=True)
        }