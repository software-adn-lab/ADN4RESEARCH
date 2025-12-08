from typing import List, Dict, Any
from collections import defaultdict
from apps.interpretation.conclusion_assistant.models.subtheme_models import SubTheme
from apps.interpretation.conclusion_assistant.models.normalization_models import (
    NormalizedCode,
)
from apps.extraction.core.models import PaperExtraction
from ...structured_data.aggregators import UnifiedStudyDTO


class SynthesisGenerator:
    """
    Generates data for thematic synthesis visualizations.
    """

    def generate_theme_coverage(self, studies: List[UnifiedStudyDTO]) -> Dict[str, Any]:
        if not studies:
            return {"matrix": [], "themes": [], "studies": []}

        # 1. Get study IDs
        try:
            # Ensure study_ids are integers as per PaperExtraction model
            study_ids = [int(s.study_id) for s in studies if str(s.study_id).isdigit()]
        except (ValueError, TypeError):
            return {"matrix": [], "themes": [], "studies": []}

        if not study_ids:
            return {"matrix": [], "themes": [], "studies": []}

        # 2. Identify Project Context
        first_extraction = PaperExtraction.objects.filter(study_id=study_ids[0]).first()
        if not first_extraction:
            return {"matrix": [], "themes": [], "studies": []}

        project_id = first_extraction.project_id

        # 3. Build Mapping: Original Tag -> Theme(s)

        # Get NormalizedCodes for this project
        normalized_codes = NormalizedCode.objects.filter(project_id=project_id)

        # Map: Normalized Code Name -> List of Original Tag Names
        norm_code_to_tags = {nc.code: nc.original_codes for nc in normalized_codes}
        valid_norm_codes = set(norm_code_to_tags.keys())

        # Get SubThemes that use these normalized codes
        # Since we can't easily filter JSONField list containment for many items in all DBs,
        # and assuming SubTheme count is manageable, we fetch all and filter in Python.
        all_subthemes = SubTheme.objects.select_related("theme").all()

        tag_to_themes = defaultdict(set)

        for st in all_subthemes:
            # Check if this subtheme uses any of our project's normalized codes
            intersecting_codes = [c for c in st.central_codes if c in valid_norm_codes]

            if intersecting_codes:
                theme_name = st.theme.name
                for code in intersecting_codes:
                    original_tags = norm_code_to_tags.get(code, [])
                    for tag in original_tags:
                        tag_to_themes[tag].add(theme_name)

        # 4. Query Evidence (Quotes & Tags)
        extractions = PaperExtraction.objects.filter(
            study_id__in=study_ids
        ).prefetch_related("quotes__tags")

        # 5. Construct Matrix Data
        study_theme_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        all_found_themes = set()

        for extraction in extractions:
            s_id_str = str(extraction.study_id)
            for quote in extraction.quotes.all():
                for tag in quote.tags.all():
                    if tag.name in tag_to_themes:
                        for theme_name in tag_to_themes[tag.name]:
                            study_theme_counts[s_id_str][theme_name] += 1
                            all_found_themes.add(theme_name)

        sorted_themes = sorted(list(all_found_themes))

        matrix_data = []
        for study in studies:
            s_id = str(study.study_id)
            row = {"study": study.title, "study_id": s_id}
            for theme in sorted_themes:
                row[theme] = study_theme_counts[s_id][theme]

            matrix_data.append(row)

        return {
            "matrix": matrix_data,
            "themes": sorted_themes,
            "studies": [s.title for s in studies],
        }
