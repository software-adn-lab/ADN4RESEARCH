"""Result normalization components for academic sources."""

from .result_normalizer import ResultNormalizer
from .ieee_result_normalizer import IeeeResultNormalizer
from .scopus_result_normalizer import ScopusResultNormalizer

__all__ = ['ResultNormalizer', 'IeeeResultNormalizer', 'ScopusResultNormalizer']
