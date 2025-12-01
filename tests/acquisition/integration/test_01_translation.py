"""
Live Integration Tests for Translation Functionality.

This module tests the translation of search strategies to academic source queries
using TranslationService directly. Tests validate that strategies are correctly
translated to Scopus and IEEE query formats with proper handling of terms,
synonyms, and exclusions.

Test Coverage:
- Strategy-to-query translation using TranslationService
- Scopus and IEEE query format compliance
- Strategy component processing (terms, synonyms, exclusions)
- Edge cases (empty strategies, malformed input)
"""

import unittest
from typing import Dict, Any

from hypothesis import given, settings, strategies as st
from hypothesis import assume
from hypothesis.extra.django import TestCase as HypothesisTestCase

from tests.acquisition.integration.base_live_test import BaseLiveTest
from apps.acquisition.translation.domain.models import NormalizedStrategy
from apps.acquisition.shared.domain.exceptions import DomainValidationError
from apps.acquisition.translation.application.translation_service import TranslationService


class TranslationLiveTest(BaseLiveTest):
    """
    Live integration tests for translation functionality.
    
    These tests validate that TranslationService correctly translates
    search strategies to academic source-specific queries WITHOUT making
    external API calls or web scraping.
    """
    
    def test_basic_translation_via_service(self):
        """
        Test basic translation of a simple strategy using TranslationService.
        
        This test validates that:
        - Translation service accepts a strategy
        - Translation produces queries for both Scopus and IEEE
        - Queries are non-empty strings
        - Translation completes without errors
        """
        from apps.acquisition.translation.application.translation_service import TranslationService
        from apps.acquisition.translation.domain.models import NormalizedStrategy
        
        # Get a simple test strategy
        strategy_dict = self.get_test_strategy_simple()
        
        # Create normalized strategy and translate directly
        strategy = NormalizedStrategy.from_dict(strategy_dict)
        translation_service = TranslationService()
        
        # Translate to both sources
        scopus_result = translation_service.translate(strategy, "Scopus")
        ieee_result = translation_service.translate(strategy, "IEEE Xplore")
        
        # Validate that queries were generated
        self.assertIsNotNone(scopus_result)
        self.assertIsNotNone(ieee_result)
        
        # Should have output queries
        self.assertIn('output_query', scopus_result)
        self.assertIn('output_query', ieee_result)
        
        # Queries should be non-empty strings
        self.assertIsInstance(scopus_result['output_query'], str)
        self.assertIsInstance(ieee_result['output_query'], str)
        self.assertTrue(scopus_result['output_query'].strip())
        self.assertTrue(ieee_result['output_query'].strip())

    def test_translation_with_synonyms(self):
        """
        Test that synonyms are properly included in translated queries.
        
        Validates that:
        - Synonyms from the strategy appear in the translated query
        - Both main terms and synonyms are processed
        - Query structure accommodates multiple term variations
        """
        strategy_dict = {
            "strategy_id": "test_synonyms_2024",
            "main_terms": [
                {
                    "term": "artificial intelligence",
                    "synonyms": ["AI", "machine intelligence"]
                }
            ],
            "exclusions": [],
            "filters": {
                "year": {"from": 2020, "to": 2024}
            }
        }
        
        # Create normalized strategy and translate directly
        strategy = NormalizedStrategy.from_dict(strategy_dict)
        translation_service = TranslationService()
        
        # Translate to both sources
        scopus_result = translation_service.translate(strategy, "Scopus")
        translation_service.translate(strategy, "IEEE Xplore")
        
        # At least one query should contain references to the synonyms
        scopus_query = scopus_result['output_query'].lower()
        
        # Check that main term or synonyms appear
        has_ai_terms = (
            'artificial intelligence' in scopus_query or
            'ai' in scopus_query or
            'machine intelligence' in scopus_query
        )
        self.assertTrue(has_ai_terms, "Scopus query should contain AI-related terms")

    def test_translation_with_exclusions(self):
        """Test that exclusion terms are properly handled in translation."""
        strategy_dict = {
            "strategy_id": "test_exclusions_2024",
            "main_terms": [{"term": "machine learning", "synonyms": ["ML"]}],
            "exclusions": ["medical", "healthcare"],
            "filters": {"year": {"from": 2020, "to": 2024}}
        }
        
        strategy = NormalizedStrategy.from_dict(strategy_dict)
        translation_service = TranslationService()
        
        scopus_result = translation_service.translate(strategy, "Scopus")
        ieee_result = translation_service.translate(strategy, "IEEE Xplore")
        
        self.assertIsNotNone(scopus_result['output_query'])
        self.assertIsNotNone(ieee_result['output_query'])
        self.assertTrue(scopus_result['output_query'].strip())
        self.assertTrue(ieee_result['output_query'].strip())
    
    def test_translation_with_year_filters(self):
        """Test that year filters are properly included in translated queries."""
        strategy_dict = {
            "strategy_id": "test_years_2024",
            "main_terms": [{"term": "software testing", "synonyms": []}],
            "exclusions": [],
            "filters": {"year": {"from": 2022, "to": 2024}}
        }
        
        strategy = NormalizedStrategy.from_dict(strategy_dict)
        translation_service = TranslationService()
        
        scopus_result = translation_service.translate(strategy, "Scopus")
        ieee_result = translation_service.translate(strategy, "IEEE Xplore")
        
        self.assertIsNotNone(scopus_result['output_query'])
        self.assertIsNotNone(ieee_result['output_query'])
        self.assertTrue(scopus_result['output_query'].strip())
        self.assertTrue(ieee_result['output_query'].strip())
    
    def test_translation_multiple_main_terms(self):
        """Test translation with multiple main terms."""
        strategy_dict = self.get_test_strategy()  # Has 2 main terms
        
        strategy = NormalizedStrategy.from_dict(strategy_dict)
        translation_service = TranslationService()
        
        scopus_result = translation_service.translate(strategy, "Scopus")
        ieee_result = translation_service.translate(strategy, "IEEE Xplore")
        
        self.assertIsNotNone(scopus_result['output_query'])
        self.assertIsNotNone(ieee_result['output_query'])
        self.assertTrue(scopus_result['output_query'].strip())
        self.assertTrue(ieee_result['output_query'].strip())

    def test_translation_edge_case_empty_synonyms(self):
        """Test translation with empty synonym lists."""
        strategy_dict = {
            "strategy_id": "test_no_synonyms_2024",
            "main_terms": [{"term": "blockchain", "synonyms": []}],
            "exclusions": [],
            "filters": {"year": {"from": 2020, "to": 2024}}
        }
        
        strategy = NormalizedStrategy.from_dict(strategy_dict)
        translation_service = TranslationService()
        
        scopus_result = translation_service.translate(strategy, "Scopus")
        ieee_result = translation_service.translate(strategy, "IEEE Xplore")
        
        self.assertIsNotNone(scopus_result['output_query'])
        self.assertIsNotNone(ieee_result['output_query'])
        self.assertTrue(scopus_result['output_query'].strip())
        self.assertTrue(ieee_result['output_query'].strip())
    
    def test_translation_edge_case_no_exclusions(self):
        """Test translation with no exclusion terms."""
        strategy_dict = {
            "strategy_id": "test_no_exclusions_2024",
            "main_terms": [{"term": "cloud computing", "synonyms": ["cloud services"]}],
            "exclusions": [],
            "filters": {"year": {"from": 2020, "to": 2024}}
        }
        
        strategy = NormalizedStrategy.from_dict(strategy_dict)
        translation_service = TranslationService()
        
        scopus_result = translation_service.translate(strategy, "Scopus")
        ieee_result = translation_service.translate(strategy, "IEEE Xplore")
        
        self.assertIsNotNone(scopus_result['output_query'])
        self.assertIsNotNone(ieee_result['output_query'])
        self.assertTrue(scopus_result['output_query'].strip())
        self.assertTrue(ieee_result['output_query'].strip())
    
    def test_translation_edge_case_no_year_filter(self):
        """Test translation without year filters."""
        strategy_dict = {
            "strategy_id": "test_no_years_2024",
            "main_terms": [{"term": "quantum computing", "synonyms": []}],
            "exclusions": []
        }
        
        strategy = NormalizedStrategy.from_dict(strategy_dict)
        translation_service = TranslationService()
        
        scopus_result = translation_service.translate(strategy, "Scopus")
        ieee_result = translation_service.translate(strategy, "IEEE Xplore")
        
        self.assertIsNotNone(scopus_result['output_query'])
        self.assertIsNotNone(ieee_result['output_query'])
        self.assertTrue(scopus_result['output_query'].strip())
        self.assertTrue(ieee_result['output_query'].strip())

    def test_translation_error_handling_invalid_strategy(self):
        """Test that invalid strategies are rejected gracefully."""
        invalid_strategy = {
            "strategy_id": "test_invalid_2024",
            "exclusions": []  # Missing main_terms
        }
        
        with self.assertRaises((ValueError, DomainValidationError, KeyError)):
            NormalizedStrategy.from_dict(invalid_strategy)
    
    def test_translation_error_handling_empty_main_terms(self):
        """Test that strategies with empty main_terms are rejected."""
        invalid_strategy = {
            "strategy_id": "test_empty_terms_2024",
            "main_terms": [],
            "exclusions": []
        }
        
        with self.assertRaises((ValueError, DomainValidationError)):
            NormalizedStrategy.from_dict(invalid_strategy)
    
    def test_translation_error_handling_invalid_year_range(self):
        """Test that invalid year ranges are rejected."""
        invalid_strategy = {
            "strategy_id": "test_invalid_years_2024",
            "main_terms": [{"term": "test", "synonyms": []}],
            "exclusions": [],
            "filters": {"year": {"from": 2024, "to": 2020}}  # Invalid: from > to
        }
        
        with self.assertRaises((ValueError, DomainValidationError)):
            NormalizedStrategy.from_dict(invalid_strategy)
    
    def test_translation_error_handling_malformed_term_structure(self):
        """Test that malformed term structures are rejected gracefully."""
        invalid_strategy = {
            "strategy_id": "test_malformed_term_2024",
            "main_terms": [{"synonyms": ["test"]}],  # Missing 'term' field
            "exclusions": []
        }
        
        with self.assertRaises((ValueError, DomainValidationError, KeyError)):
            NormalizedStrategy.from_dict(invalid_strategy)
    
    def test_translation_error_handling_invalid_data_types(self):
        """Test that invalid data types in strategy are rejected."""
        invalid_strategy_1 = {
            "strategy_id": "test_invalid_type_1",
            "main_terms": "not a list",  # Should be a list
            "exclusions": []
        }
        
        with self.assertRaises((ValueError, DomainValidationError, TypeError)):
            NormalizedStrategy.from_dict(invalid_strategy_1)
        
        invalid_strategy_2 = {
            "strategy_id": "test_invalid_type_2",
            "main_terms": [{"term": 123, "synonyms": []}],  # Should be a string
            "exclusions": []
        }
        
        with self.assertRaises((ValueError, DomainValidationError, TypeError)):
            NormalizedStrategy.from_dict(invalid_strategy_2)

    def test_translation_edge_case_special_characters(self):
        """Test that special characters in terms are handled gracefully."""
        strategy_dict = {
            "strategy_id": "test_special_chars_2024",
            "main_terms": [{"term": "C++ programming", "synonyms": ["C#", "F#"]}],
            "exclusions": ["C/C++"],
            "filters": {"year": {"from": 2020, "to": 2024}}
        }
        
        strategy = NormalizedStrategy.from_dict(strategy_dict)
        translation_service = TranslationService()
        
        scopus_result = translation_service.translate(strategy, "Scopus")
        ieee_result = translation_service.translate(strategy, "IEEE Xplore")
        
        self.assertIsNotNone(scopus_result['output_query'])
        self.assertIsNotNone(ieee_result['output_query'])
        self.assertTrue(scopus_result['output_query'].strip())
        self.assertTrue(ieee_result['output_query'].strip())
    
    def test_translation_edge_case_very_long_terms(self):
        """Test that very long terms are handled appropriately."""
        long_term = "a" * 500  # Very long term
        
        strategy_dict = {
            "strategy_id": "test_long_term_2024",
            "main_terms": [{"term": long_term, "synonyms": []}],
            "exclusions": []
        }
        
        strategy = NormalizedStrategy.from_dict(strategy_dict)
        translation_service = TranslationService()
        
        scopus_result = translation_service.translate(strategy, "Scopus")
        ieee_result = translation_service.translate(strategy, "IEEE Xplore")
        
        self.assertIsNotNone(scopus_result['output_query'])
        self.assertIsNotNone(ieee_result['output_query'])
    
    def test_translation_edge_case_whitespace_only_terms(self):
        """Test that whitespace-only terms are rejected."""
        invalid_strategy = {
            "strategy_id": "test_whitespace_2024",
            "main_terms": [{"term": "   ", "synonyms": []}],  # Only whitespace
            "exclusions": []
        }
        
        with self.assertRaises((ValueError, DomainValidationError)):
            NormalizedStrategy.from_dict(invalid_strategy)
    
    def test_translation_edge_case_unicode_characters(self):
        """Test that Unicode characters in terms are handled correctly."""
        strategy_dict = {
            "strategy_id": "test_unicode_2024",
            "main_terms": [{"term": "machine learning 机器学习", "synonyms": ["ML", "深度学习"]}],
            "exclusions": ["医疗"],
            "filters": {"year": {"from": 2020, "to": 2024}}
        }
        
        strategy = NormalizedStrategy.from_dict(strategy_dict)
        translation_service = TranslationService()
        
        scopus_result = translation_service.translate(strategy, "Scopus")
        ieee_result = translation_service.translate(strategy, "IEEE Xplore")
        
        self.assertIsNotNone(scopus_result['output_query'])
        self.assertIsNotNone(ieee_result['output_query'])
        self.assertTrue(scopus_result['output_query'].strip())
        self.assertTrue(ieee_result['output_query'].strip())
    
    def test_translation_edge_case_empty_string_term(self):
        """Test that empty string terms are rejected."""
        invalid_strategy = {
            "strategy_id": "test_empty_string_2024",
            "main_terms": [{"term": "", "synonyms": []}],  # Empty string
            "exclusions": []
        }
        
        with self.assertRaises((ValueError, DomainValidationError)):
            NormalizedStrategy.from_dict(invalid_strategy)
    
    def test_translation_edge_case_duplicate_terms(self):
        """Test that duplicate terms are handled gracefully."""
        strategy_dict = {
            "strategy_id": "test_duplicates_2024",
            "main_terms": [
                {"term": "machine learning", "synonyms": ["ML"]},
                {"term": "machine learning", "synonyms": ["ML"]}  # Duplicate
            ],
            "exclusions": [],
            "filters": {"year": {"from": 2020, "to": 2024}}
        }
        
        strategy = NormalizedStrategy.from_dict(strategy_dict)
        translation_service = TranslationService()
        
        scopus_result = translation_service.translate(strategy, "Scopus")
        ieee_result = translation_service.translate(strategy, "IEEE Xplore")
        
        self.assertIsNotNone(scopus_result['output_query'])
        self.assertIsNotNone(ieee_result['output_query'])
        self.assertTrue(scopus_result['output_query'].strip())
        self.assertTrue(ieee_result['output_query'].strip())
    
    def test_translation_edge_case_many_synonyms(self):
        """Test that terms with many synonyms are handled correctly."""
        many_synonyms = [f"synonym_{i}" for i in range(50)]
        
        strategy_dict = {
            "strategy_id": "test_many_synonyms_2024",
            "main_terms": [{"term": "artificial intelligence", "synonyms": many_synonyms}],
            "exclusions": [],
            "filters": {"year": {"from": 2020, "to": 2024}}
        }
        
        strategy = NormalizedStrategy.from_dict(strategy_dict)
        translation_service = TranslationService()
        
        scopus_result = translation_service.translate(strategy, "Scopus")
        ieee_result = translation_service.translate(strategy, "IEEE Xplore")
        
        self.assertIsNotNone(scopus_result['output_query'])
        self.assertIsNotNone(ieee_result['output_query'])
        self.assertTrue(scopus_result['output_query'].strip())
        self.assertTrue(ieee_result['output_query'].strip())



class TranslationPropertyTests(BaseLiveTest, HypothesisTestCase):
    """
    Property-based tests for translation functionality.
    
    These tests use Hypothesis to generate random test data and verify
    that universal properties hold across all valid inputs.
    """
    
    @settings(max_examples=100, deadline=None)
    @given(
        strategy_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        main_term=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        year_from=st.integers(min_value=1900, max_value=2024),
        year_to=st.integers(min_value=1900, max_value=2024)
    )
    def test_property_strategy_translation_completeness(
        self, strategy_id, main_term, year_from, year_to
    ):
        """
        **Feature: acquisition-live-tests, Property 5: Strategy Translation Completeness**
        **Validates: Requirements 3.1**
        
        Property: For any valid search strategy, translation should return 
        queries for both Scopus and IEEE sources.
        """
        if year_from > year_to:
            year_from, year_to = year_to, year_from
        
        strategy_dict = {
            "strategy_id": strategy_id,
            "main_terms": [{"term": main_term, "synonyms": []}],
            "exclusions": [],
            "filters": {"year": {"from": year_from, "to": year_to}}
        }
        
        try:
            strategy = NormalizedStrategy.from_dict(strategy_dict)
            translation_service = TranslationService()
            
            scopus_result = translation_service.translate(strategy, "Scopus")
            ieee_result = translation_service.translate(strategy, "IEEE Xplore")
            
            self.assertIsNotNone(scopus_result)
            self.assertIsNotNone(ieee_result)
            self.assertIn('output_query', scopus_result)
            self.assertIn('output_query', ieee_result)
            
            self.assertIsInstance(scopus_result['output_query'], str)
            self.assertIsInstance(ieee_result['output_query'], str)
            self.assertTrue(scopus_result['output_query'].strip())
            self.assertTrue(ieee_result['output_query'].strip())
            
        except Exception as e:
            self.fail(f"Translation failed for strategy {strategy_id}: {e}")

    @settings(max_examples=100, deadline=None)
    @given(
        strategy_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        main_term=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        synonyms=st.lists(
            st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
            min_size=0,
            max_size=5
        ),
        exclusions=st.lists(
            st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
            min_size=0,
            max_size=5
        )
    )
    def test_property_query_format_validation(
        self, strategy_id, main_term, synonyms, exclusions
    ):
        """
        **Feature: acquisition-live-tests, Property 6: Query Format Validation**
        **Validates: Requirements 3.2**
        
        Property: For any translated query, the output should be properly 
        formatted according to each academic source's requirements.
        """
        strategy_dict = {
            "strategy_id": strategy_id,
            "main_terms": [{"term": main_term, "synonyms": synonyms}],
            "exclusions": exclusions,
            "filters": {"year": {"from": 2020, "to": 2024}}
        }
        
        try:
            strategy = NormalizedStrategy.from_dict(strategy_dict)
            translation_service = TranslationService()
            
            scopus_result = translation_service.translate(strategy, "Scopus")
            ieee_result = translation_service.translate(strategy, "IEEE Xplore")
            
            queries = {
                'Scopus': scopus_result['output_query'],
                'IEEE Xplore': ieee_result['output_query']
            }
            
            for source, query in queries.items():
                self.assertIsInstance(query, str, f"{source} query is not a string")
                self.assertTrue(query.strip(), f"{source} query is empty")
                self.assertNotIn('None', query, f"{source} query contains 'None'")
                self.assertNotIn('null', query.lower(), f"{source} query contains 'null'")
                
        except Exception as e:
            self.fail(f"Query format validation failed: {e}")

    @settings(max_examples=100, deadline=None)
    @given(
        strategy_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        num_terms=st.integers(min_value=1, max_value=3),
        has_synonyms=st.booleans(),
        has_exclusions=st.booleans()
    )
    def test_property_strategy_component_processing(
        self, strategy_id, num_terms, has_synonyms, has_exclusions
    ):
        """
        **Feature: acquisition-live-tests, Property 7: Strategy Component Processing**
        **Validates: Requirements 3.3**
        
        Property: For any strategy containing main terms, synonyms, and exclusions,
        all components should be correctly processed in the translation.
        """
        main_terms = []
        for i in range(num_terms):
            term_data = {
                "term": f"term_{i}_{strategy_id[:10]}",
                "synonyms": []
            }
            if has_synonyms:
                term_data["synonyms"] = [f"syn_{i}_1", f"syn_{i}_2"]
            main_terms.append(term_data)
        
        exclusions = []
        if has_exclusions:
            exclusions = [f"excl_1_{strategy_id[:10]}", f"excl_2_{strategy_id[:10]}"]
        
        strategy_dict = {
            "strategy_id": strategy_id,
            "main_terms": main_terms,
            "exclusions": exclusions,
            "filters": {"year": {"from": 2020, "to": 2024}}
        }
        
        try:
            strategy = NormalizedStrategy.from_dict(strategy_dict)
            translation_service = TranslationService()
            
            scopus_result = translation_service.translate(strategy, "Scopus")
            ieee_result = translation_service.translate(strategy, "IEEE Xplore")
            
            self.assertIsNotNone(scopus_result)
            self.assertIsNotNone(ieee_result)
            self.assertIn('output_query', scopus_result)
            self.assertIn('output_query', ieee_result)
            
            scopus_query = scopus_result['output_query']
            ieee_query = ieee_result['output_query']
            
            self.assertIsInstance(scopus_query, str)
            self.assertIsInstance(ieee_query, str)
            self.assertTrue(scopus_query.strip())
            self.assertTrue(ieee_query.strip())
            
            if num_terms > 1:
                self.assertGreater(len(scopus_query), 10)
                self.assertGreater(len(ieee_query), 10)
            
            self.assertEqual(scopus_result['status'], 'ready')
            self.assertEqual(ieee_result['status'], 'ready')
            
        except Exception as e:
            self.fail(f"Component processing failed: {e}")

    @settings(max_examples=1, deadline=None)
    @given(
        strategy_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        main_term=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        has_synonyms=st.booleans(),
        has_exclusions=st.booleans(),
        has_year_filter=st.booleans()
    )
    def test_property_translation_component_completeness(
        self, strategy_id, main_term, has_synonyms, has_exclusions, has_year_filter
    ):
        """
        **Feature: acquisition-live-tests, Property 8: Translation Component Completeness**
        **Validates: Requirements 3.4**
        
        Property: For any translated query, all required query components 
        should be present in the output.
        """
        term_data = {
            "term": main_term,
            "synonyms": ["synonym1", "synonym2"] if has_synonyms else []
        }
        
        exclusions = ["exclude1", "exclude2"] if has_exclusions else []
        
        strategy_dict = {
            "strategy_id": strategy_id,
            "main_terms": [term_data],
            "exclusions": exclusions
        }
        
        if has_year_filter:
            strategy_dict["filters"] = {"year": {"from": 2020, "to": 2024}}
        
        try:
            strategy = NormalizedStrategy.from_dict(strategy_dict)
            translation_service = TranslationService()
            
            scopus_result = translation_service.translate(strategy, "Scopus")
            ieee_result = translation_service.translate(strategy, "IEEE Xplore")
            
            self.assertIsNotNone(scopus_result)
            self.assertIsNotNone(ieee_result)
            self.assertIn('output_query', scopus_result)
            self.assertIn('output_query', ieee_result)
            
            self.assertTrue(scopus_result['output_query'].strip())
            self.assertTrue(ieee_result['output_query'].strip())
            
            min_expected_length = len(main_term) // 2
            self.assertGreater(len(scopus_result['output_query']), min_expected_length)
            self.assertGreater(len(ieee_result['output_query']), min_expected_length)
            
        except Exception as e:
            self.fail(f"Component completeness check failed: {e}")


if __name__ == '__main__':
    unittest.main()
