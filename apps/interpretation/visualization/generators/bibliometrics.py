from typing import List, Dict, Any
from collections import Counter
from ...structured_data.aggregators import UnifiedStudyDTO


class BibliometricGenerator:
    """
    Generates data for bibliometric visualizations.
    """

    def generate_studies_per_year(
        self, studies: List[UnifiedStudyDTO]
    ) -> Dict[str, Any]:
        years = [s.year for s in studies if s.year is not None]
        counts = Counter(years)
        sorted_years = sorted(counts.keys())

        return {
            "labels": sorted_years,
            "data": [counts[y] for y in sorted_years],
            "title": "Studies per Year",
        }

    def generate_source_distribution(
        self, studies: List[UnifiedStudyDTO]
    ) -> Dict[str, Any]:
        sources = [s.source for s in studies if s.source]
        counts = Counter(sources)

        return {
            "labels": list(counts.keys()),
            "data": list(counts.values()),
            "title": "Studies by Source",
        }
