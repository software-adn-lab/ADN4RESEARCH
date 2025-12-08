from typing import List, Dict, Any
from apps.interpretation.structured_data.aggregators import UnifiedStudyDTO
from .generators.bibliometrics import BibliometricGenerator
from .generators.synthesis import SynthesisGenerator


class ResultsVisualizationEngine:
    """
    Facade for the Results Visualization Engine component.
    Generates visualization data from structured study lists.
    """

    def __init__(self):
        self.bibliometrics = BibliometricGenerator()
        self.synthesis = SynthesisGenerator()

    def generate_dashboard_data(self, studies: List[UnifiedStudyDTO]) -> Dict[str, Any]:
        """
        Generates a complete set of data for the interpretation dashboard.
        """
        return {
            "bibliometrics": {
                "years": self.bibliometrics.generate_studies_per_year(studies),
                "sources": self.bibliometrics.generate_source_distribution(studies),
            },
            "synthesis": {"coverage": self.synthesis.generate_theme_coverage(studies)},
            "stats": {"total_studies": len(studies)},
        }
