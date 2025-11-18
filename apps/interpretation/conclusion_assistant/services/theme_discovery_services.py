"""Services for AI-driven theme discovery and code normalization."""

from django.db import transaction
from typing import List, Dict, Any, Optional
import logging
from .llm_clients import get_default_client

from apps.interpretation.conclusion_assistant.models import (
    InitialCode,
    CodeNormalizationProposal,
    NormalizedCode,
    ThemeDiscoveryProposal,
    AnalysisTrace,
    Theme,
)

logger = logging.getLogger(__name__)


class ThemeDiscoveryService:
    """
    Service for AI-driven theme discovery and code normalization.
    Follows the architecture defined in the C4 diagram:
    - Study Quality Evaluator component
    - Structured Data Manager component
    """

    def __init__(self, llm_client=None):
        """Initialize the service with an LLM client."""
        self.llm_client = llm_client or get_default_client()

    @transaction.atomic
    def load_initial_codes(
        self, codes_data: List[Dict[str, Any]], project=None
    ) -> List[InitialCode]:
        """
        Load initial codes from the extraction module.

        Args:
            codes_data: List of dicts with 'code' and 'frequency' keys
            project: Optional project reference

        Returns:
            List of InitialCode objects created
        """
        initial_codes = []
        for code_info in codes_data:
            code, created = InitialCode.objects.get_or_create(
                code=code_info["code"],
                project=project,
                defaults={"frequency": code_info.get("frequency", 1)},
            )
            if not created:
                code.frequency = code_info.get("frequency", 1)
                code.save(update_fields=["frequency", "modified_at"])
            initial_codes.append(code)

        return initial_codes

    @transaction.atomic
    def propose_code_normalization(
        self, project=None
    ) -> List[CodeNormalizationProposal]:
        """
        Activate intelligent code normalization.
        Uses AI to analyze initial codes and propose merges/splits.

        Args:
            project: Optional project to scope the analysis

        Returns:
            List of CodeNormalizationProposal objects
        """
        # Get all initial codes
        initial_codes_qs = InitialCode.objects.all()
        if project:
            initial_codes_qs = initial_codes_qs.filter(project=project)

        initial_codes = list(initial_codes_qs)

        if not initial_codes:
            logger.warning("No initial codes found for normalization")
            return []

        # Prepare data for LLM
        codes_data = [
            {"code": code.code, "frequency": code.frequency} for code in initial_codes
        ]

        # Call LLM to analyze and propose normalizations
        proposals_data = self.llm_client.propose_code_normalization(codes_data) or [
            {
                "normalized_code": "Normalización de códigos no encontrada",
                "original_codes": ["Normalización de códigos no encontrada"],
                "rationale": "Normalización de códigos no encontrada",
                "project": project,
                "status": CodeNormalizationProposal.ProposalStatus.PENDING,
            }
        ]

        # Create proposal objects
        proposals = []
        for proposal_info in proposals_data:
            proposal = CodeNormalizationProposal.objects.create(
                normalized_code=proposal_info["normalized_code"],
                original_codes=proposal_info["original_codes"],
                rationale=proposal_info.get("rationale", ""),
                project=project,
                status=CodeNormalizationProposal.ProposalStatus.PENDING,
            )
            proposals.append(proposal)

        logger.info("Created %d normalization proposals", len(proposals))
        return proposals

    @transaction.atomic
    def accept_normalization_proposals(
        self, proposal_ids: List[int], reviewer
    ) -> List[NormalizedCode]:
        """
        Accept proposed code normalizations and persist them.

        Args:
            proposal_ids: List of proposal IDs to accept
            reviewer: User who reviewed and accepted

        Returns:
            List of NormalizedCode objects created
        """
        # Accept both PENDING and already ACCEPTED proposals (but not create duplicates)
        proposals = CodeNormalizationProposal.objects.filter(
            id__in=proposal_ids, status__in=[
                CodeNormalizationProposal.ProposalStatus.PENDING,
                CodeNormalizationProposal.ProposalStatus.ACCEPTED
            ]
        )

        normalized_codes = []
        for proposal in proposals:
            # Check if a normalized code already exists for this proposal
            existing_code = NormalizedCode.objects.filter(proposal=proposal).first()
            if existing_code:
                logger.info("Normalized code already exists for proposal %d, skipping", proposal.id)
                normalized_codes.append(existing_code)
                continue
            
            # Update proposal status
            proposal.status = CodeNormalizationProposal.ProposalStatus.ACCEPTED
            proposal.reviewed_by = reviewer
            proposal.save(update_fields=["status", "reviewed_by", "modified_at"])

            # Calculate total frequency from original codes
            total_frequency = sum(
                InitialCode.objects.filter(code=orig_code, project=proposal.project)
                .values_list("frequency", flat=True)
                .first()
                or 0
                for orig_code in proposal.original_codes
            )

            # Create normalized code
            normalized_code = NormalizedCode.objects.create(
                code=proposal.normalized_code,
                original_codes=proposal.original_codes,
                frequency=total_frequency,
                proposal=proposal,
                project=proposal.project,
            )
            normalized_codes.append(normalized_code)

        logger.info("Accepted %d normalization proposals", len(normalized_codes))
        return normalized_codes

    @transaction.atomic
    def propose_theme_structure(self, project=None) -> List[ThemeDiscoveryProposal]:
        """
        Request AI to generate high-level theme structure.
        Emulates Grounded Theory methodology.

        Args:
            project: Optional project to scope the analysis

        Returns:
            List of ThemeDiscoveryProposal objects
        """
        # Get normalized codes
        normalized_codes_qs = NormalizedCode.objects.all()
        if project:
            normalized_codes_qs = normalized_codes_qs.filter(project=project)

        normalized_codes = list(normalized_codes_qs)

        if not normalized_codes:
            logger.warning("No normalized codes found for theme generation")
            return []

        # Prepare data for LLM
        codes_data = [
            {
                "code": code.code,
                "frequency": code.frequency,
                "rq_focus": code.research_question_focus,
            }
            for code in normalized_codes
        ]

        # Call LLM to propose theme structure
        theme_proposals_data = self.llm_client.propose_theme_structure(codes_data)

        # Create theme proposal objects
        proposals = []
        for theme_info in theme_proposals_data:
            proposal = ThemeDiscoveryProposal.objects.create(
                theme_name=theme_info["theme_name"],
                theme_description=theme_info.get("description", ""),
                research_question_focus=theme_info.get("rq_focus", ""),
                proposed_subthemes=theme_info.get("subthemes", []),
                rationale=theme_info.get("rationale", ""),
                project=project,
                status=ThemeDiscoveryProposal.ProposalStatus.PENDING,
            )

            # Link codes to proposal
            code_names = theme_info.get("codes", [])
            codes_to_link = normalized_codes_qs.filter(code__in=code_names)
            proposal.codes_used.set(codes_to_link)

            proposals.append(proposal)

        logger.info("Created %d theme proposals", len(proposals))
        return proposals

    @transaction.atomic
    def accept_and_create_themes(
        self, proposal_id: int, reviewer, modifications: Optional[Dict[str, Any]] = None
    ) -> List[Theme]:
        """
        Accept theme proposal and create Theme and SubTheme objects.

        Args:
            proposal_id: ID of the proposal to accept
            reviewer: User who reviewed and accepted
            modifications: Optional dict with researcher modifications

        Returns:
            List of Theme objects created
        """
        proposal = ThemeDiscoveryProposal.objects.get(id=proposal_id)

        # Store original proposal for tracing
        original_proposal = {
            "theme_name": proposal.theme_name,
            "theme_description": proposal.theme_description,
            "subthemes": proposal.proposed_subthemes,
            "rationale": proposal.rationale,
        }

        # Apply modifications if provided
        if modifications:
            if "theme_name" in modifications:
                proposal.theme_name = modifications["theme_name"]
            if "theme_description" in modifications:
                proposal.theme_description = modifications["theme_description"]
            if "subthemes" in modifications:
                proposal.proposed_subthemes = modifications["subthemes"]

            proposal.status = ThemeDiscoveryProposal.ProposalStatus.MODIFIED
        else:
            proposal.status = ThemeDiscoveryProposal.ProposalStatus.ACCEPTED

        proposal.reviewed_by = reviewer
        proposal.save(
            update_fields=[
                "theme_name",
                "theme_description",
                "proposed_subthemes",
                "status",
                "reviewed_by",
                "modified_at",
            ]
        )

        # Create Theme (Level 1 only, no subthemes)
        theme = Theme.objects.create(
            name=proposal.theme_name,
            description=proposal.theme_description,
            research_question=proposal.research_question_focus,
            created_by=reviewer,
        )

        # NOTE: No SubThemes are created for Level 1 themes
        # Subthemes can be created later if needed through the SubTheme model directly

        # Create analysis trace
        AnalysisTrace.objects.create(
            trace_type=AnalysisTrace.TraceType.THEME_DISCOVERY,
            ai_proposal=original_proposal,
            researcher_modifications=modifications or {},
            final_result={
                "theme_name": theme.name,
                "theme_description": theme.description,
                "subthemes": [
                    {"name": st.name, "codes": st.central_codes}
                    for st in theme.subthemes.all()
                ],
            },
            rationale=modifications.get("rationale", "") if modifications else "",
            project=proposal.project,
            created_by=reviewer,
        )

        logger.info("Created Level 1 theme '%s' (no subthemes)", theme.name)
        return [theme]

    def get_normalization_proposals(
        self, project=None
    ) -> List[CodeNormalizationProposal]:
        """Get all pending normalization proposals."""
        qs = CodeNormalizationProposal.objects.filter(
            status=CodeNormalizationProposal.ProposalStatus.PENDING
        )
        if project:
            qs = qs.filter(project=project)
        return list(qs)

    def get_theme_proposals(self, project=None) -> List[ThemeDiscoveryProposal]:
        """Get all pending theme proposals."""
        qs = ThemeDiscoveryProposal.objects.filter(
            status=ThemeDiscoveryProposal.ProposalStatus.PENDING
        )
        if project:
            qs = qs.filter(project=project)
        return list(qs)

    def get_analysis_traces(self, project=None) -> List[AnalysisTrace]:
        """Get all analysis traces for reflexivity."""
        qs = AnalysisTrace.objects.all()
        if project:
            qs = qs.filter(project=project)
        return list(qs)
