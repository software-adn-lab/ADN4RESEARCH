"""BDD steps for AI-Driven Theme Discovery feature."""

from behave import given, when, then
from django.contrib.auth.models import User

from apps.interpretation.conclusion_assistant.models import (
    CodeNormalizationProposal,
    NormalizedCode,
    ThemeDiscoveryProposal,
    AnalysisTrace,
    Theme,
)
from apps.interpretation.conclusion_assistant.services.theme_discovery_services import (
    ThemeDiscoveryService,
)

theme_discovery_service = ThemeDiscoveryService()


# Scenario 1: Code Normalization Steps


@given(
    "que el Módulo de Interpretación ha cargado los Códigos iniciales (tags) desde el Módulo de Extracción"
)
def step_impl(context):
    """Load initial codes from the extraction module."""
    # Create a test user if not exists
    if not hasattr(context, "researcher"):
        context.researcher, _ = User.objects.get_or_create(
            username="test_researcher", defaults={"email": "researcher@test.com"}
        )

    # Parse the table and load codes
    if context.table:
        codes_data = []
        for row in context.table:
            code = row["Código Inicial"]
            frequency = int(row["Frecuencia"])
            codes_data.append({"code": code, "frequency": frequency})

        # Load codes into the system
        context.initial_codes = theme_discovery_service.load_initial_codes(
            codes_data=codes_data, project=None
        )

        assert len(context.initial_codes) == len(codes_data)


@when(
    'el Investigador activa la función "Normalización Inteligente de Códigos" en el Study Quality Evaluator'
)
def step_impl(context):
    """Activate intelligent code normalization."""
    # Call the service to propose normalizations
    context.normalization_proposals = (
        theme_discovery_service.propose_code_normalization(project=None)
    )

    # Verify proposals were created
    assert len(context.normalization_proposals) > 0
    assert all(
        p.status == CodeNormalizationProposal.ProposalStatus.PENDING
        for p in context.normalization_proposals
    )


@then(
    "el sistema (IA) debería analizar los códigos y proponer las siguientes acciones para reducir la redundancia:"
)
def step_impl(context):
    """Verify that the AI proposed code normalizations."""
    # This is a parent step for the And clauses
    assert hasattr(context, "normalization_proposals")
    assert len(context.normalization_proposals) > 0


@then(
    'Proponer la fusión de [{original_codes}] en un nuevo Código Normalizado: "{normalized_code}".'
)
def step_impl(context, original_codes, normalized_code):
    """Verify a specific normalization proposal exists."""
    # Parse the original codes list
    original_codes_list = [
        code.strip().strip("#") for code in original_codes.split(",")
    ]

    # Find matching proposal
    matching_proposal = None
    for proposal in context.normalization_proposals:
        # Normalize comparison by removing # prefix
        proposal_originals = [c.strip("#") for c in proposal.original_codes]
        if set(proposal_originals) == set(original_codes_list):
            matching_proposal = proposal
            break

    assert matching_proposal is not None, (
        f"No proposal found for merging {original_codes_list} "
        f"into {normalized_code}"
    )

    # Verify the normalized code matches (allow some flexibility)
    assert normalized_code.strip("#") in matching_proposal.normalized_code.strip("#")


@when("el Investigador acepta la lista de Códigos Normalizados propuestos")
def step_impl(context):
    """Accept the normalization proposals."""
    proposal_ids = [p.id for p in context.normalization_proposals]

    context.normalized_codes = theme_discovery_service.accept_normalization_proposals(
        proposal_ids=proposal_ids, reviewer=context.researcher
    )

    assert len(context.normalized_codes) > 0


@then(
    "el Módulo de Interpretación persiste el nuevo diccionario de códigos para su uso en la siguiente fase."
)
def step_impl(context):
    """Verify normalized codes were persisted."""
    # Check that normalized codes exist in the database
    assert len(context.normalized_codes) > 0

    # Verify all normalized codes have proper status
    for code in context.normalized_codes:
        assert code.id is not None
        assert len(code.original_codes) > 0

        # Verify the proposal was accepted
        if code.proposal:
            code.proposal.refresh_from_db()
            assert (
                code.proposal.status
                == CodeNormalizationProposal.ProposalStatus.ACCEPTED
            )


# Scenario 2: Theme Discovery Steps


@given("que el proceso de Normalización de Códigos ha sido completado")
def step_impl(context):
    """Verify code normalization is complete."""
    # If we don't have normalized codes from previous scenario, create them
    if not hasattr(context, "normalized_codes") or not context.normalized_codes:
        # Create test user
        if not hasattr(context, "researcher"):
            context.researcher, _ = User.objects.get_or_create(
                username="test_researcher", defaults={"email": "researcher@test.com"}
            )

        # Create some normalized codes for testing
        context.normalized_codes = [
            NormalizedCode.objects.create(
                code="#antipattern_detection",
                original_codes=["#antipattern_detection"],
                research_question_focus="RQ1",
                frequency=4,
            ),
            NormalizedCode.objects.create(
                code="#extracción_de_repositorios_SWH",
                original_codes=["#repository_mining", "#github"],
                research_question_focus="RQ1",
                frequency=5,
            ),
        ]

    assert len(context.normalized_codes) > 0


@given(
    "el Study Quality Evaluator dispone de los siguientes Códigos Finales (Axiomas) para la síntesis:"
)
def step_impl(context):
    """Load final normalized codes with RQ focus."""
    if context.table:
        # Clear any existing normalized codes from test
        NormalizedCode.objects.all().delete()

        for row in context.table:
            code = row["Código Final"]
            rq_focus = row["Foco de Investigación"]

            NormalizedCode.objects.create(
                code=code,
                original_codes=[code],
                research_question_focus=rq_focus,
                frequency=1,
            )

        # Refresh the list
        context.normalized_codes = list(NormalizedCode.objects.all())

        assert len(context.normalized_codes) == len(context.table.rows)


@when("el Investigador **solicita a la IA generar una estructura de temas de Nivel 1** (sin subtemas)")
def step_impl(context):
    """Request AI to generate Level 1 theme structure without subthemes."""
    context.theme_proposals = theme_discovery_service.propose_theme_structure(
        project=None
    )

    # Verify proposals were created
    assert len(context.theme_proposals) > 0
    assert all(
        p.status == ThemeDiscoveryProposal.ProposalStatus.PENDING
        for p in context.theme_proposals
    )


@then("el sistema (IA/LLM) debería, basándose en la coherencia semántica de los códigos, proponer los siguientes Temas de Nivel 1:")
def step_impl(context):
    """Verify Level 1 theme proposals were generated."""
    assert hasattr(context, "theme_proposals")
    assert len(context.theme_proposals) > 0
    
    # Verify no subthemes are present (Level 1 only)
    for proposal in context.theme_proposals:
        assert len(proposal.proposed_subthemes) == 0, (
            f"Theme '{proposal.theme_name}' should not have subthemes for Level 1"
        )


@then('Proponer el Tema 1: "{theme_name}" que agrupe:')
def step_impl(context, theme_name):
    """Verify Tema 1 proposal with specific codes."""
    # Find matching theme
    matching_theme = None
    for proposal in context.theme_proposals:
        if theme_name.lower() in proposal.theme_name.lower():
            matching_theme = proposal
            break

    assert (
        matching_theme is not None
    ), f"No theme proposal found matching '{theme_name}'"

    # Verify it groups codes from RQ1 (if table provided, check specific codes)
    if context.table and len(context.table.rows) > 0:
        # The table is a single row with multiple columns (codes)
        expected_codes = [cell for cell in context.table.rows[0].cells]
        
        theme_codes = [c.code for c in matching_theme.codes_used.all()]
        for expected_code in expected_codes:
            assert any(expected_code in code for code in theme_codes), (
                f"Expected code {expected_code} not found in theme codes: {theme_codes}"
            )
    
    # Store for later verification
    context.theme_1 = matching_theme


@then('Proponer el Tema 2: "{theme_name}" que agrupe:')
def step_impl(context, theme_name):
    """Verify Tema 2 proposal with specific codes."""
    # Find matching theme
    matching_theme = None
    for proposal in context.theme_proposals:
        if (
            theme_name.lower() in proposal.theme_name.lower()
            or "factores" in proposal.theme_name.lower()
        ):
            matching_theme = proposal
            break

    assert (
        matching_theme is not None
    ), f"No theme proposal found matching '{theme_name}'"

    # Verify it groups codes from RQ2 (if table provided, check specific codes)
    if context.table and len(context.table.rows) > 0:
        # The table is a single row with multiple columns (codes)
        expected_codes = [cell for cell in context.table.rows[0].cells]
        
        theme_codes = [c.code for c in matching_theme.codes_used.all()]
        for expected_code in expected_codes:
            assert any(expected_code in code for code in theme_codes), (
                f"Expected code {expected_code} not found in theme codes: {theme_codes}"
            )
    
    # Store for next modification step
    context.theme_2 = matching_theme


@when("el Investigador aplica **Reflexividad** y revisa las propuestas")
def step_impl(context):
    """Researcher reviews proposals with reflexivity."""
    # Just verify the proposals exist and are pending review
    assert hasattr(context, "theme_proposals")
    assert any(
        p.status == ThemeDiscoveryProposal.ProposalStatus.PENDING
        for p in context.theme_proposals
    )


@when('El Investigador **edita** el Tema 2, renombrándolo a: "{new_theme_name}".')
def step_impl(context, new_theme_name):
    """Researcher modifies a theme proposal."""
    # Find the theme to edit (stored in previous step)
    theme_to_edit = context.theme_2

    # Apply modifications
    modifications = {
        "theme_name": new_theme_name,
        "rationale": "Renombrado para mayor precisión conceptual",
    }

    # Accept with modifications
    context.final_themes = theme_discovery_service.accept_and_create_themes(
        proposal_id=theme_to_edit.id,
        reviewer=context.researcher,
        modifications=modifications,
    )

    assert len(context.final_themes) > 0


@then("el Módulo de Interpretación persiste la estructura de Temas Finales de Nivel 1 validados")
def step_impl(context):
    """Verify final Level 1 themes were persisted."""
    assert hasattr(context, "final_themes")
    assert len(context.final_themes) > 0

    # Verify themes exist in database
    for theme in context.final_themes:
        assert theme.id is not None
        assert Theme.objects.filter(id=theme.id).exists()

        # Verify NO subthemes were created (Level 1 only)
        assert theme.subthemes.count() == 0, (
            f"Theme '{theme.name}' should not have subthemes for Level 1"
        )


@then(
    "La **traza del análisis por IA** (propuesta inicial vs. estructura final) se registra para fines de rigor y trazabilidad metodológica."
)
def step_impl(context):
    """Verify analysis trace was recorded."""
    # Check that analysis traces exist
    traces = AnalysisTrace.objects.filter(
        trace_type=AnalysisTrace.TraceType.THEME_DISCOVERY
    )

    assert traces.exists(), "No analysis traces found"

    # Verify the trace has the required information
    trace = traces.first()
    assert "theme_name" in trace.ai_proposal
    assert trace.researcher_modifications is not None
    assert "theme_name" in trace.final_result
