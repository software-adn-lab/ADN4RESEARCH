from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse
import json

from apps.interpretation.conclusion_assistant.services.interpretation_services import (
    InterpretationService,
)
from apps.interpretation.conclusion_assistant.services.theme_discovery_services import (
    ThemeDiscoveryService,
)
from apps.interpretation.conclusion_assistant.models import (
    InterpretationContext,
    ConversationTrace,
    # InterpretativeProposition,  # Used in Scenario 2 - currently commented out
)
from apps.interpretation.conclusion_assistant.models.subtheme_models import SubTheme
from apps.interpretation.conclusion_assistant.models.theme_models import Theme
from apps.interpretation.conclusion_assistant.models.code_models import (
    InitialCode,
    CodeNormalizationProposal,
    NormalizedCode,
    ThemeDiscoveryProposal,
)
from apps.project.models import Project


service = InterpretationService()
theme_discovery_service = ThemeDiscoveryService()


def index(request):
    """List available themes and subthemes to start interpretation."""
    themes = Theme.objects.all().prefetch_related("subthemes")
    return render(request, "interpretation/index.html", {"themes": themes})


@require_http_methods(["POST", "GET"])
def start_interpretation(request, subtheme_id):
    subtheme = get_object_or_404(SubTheme, id=subtheme_id)
    try:
        context, _ = service.initiate_interpretation_context(subtheme)
        messages.success(request, "Asistencia iniciada.")
        return redirect(reverse("interpretation:conversation", args=[context.id]))
    except Exception as e:
        messages.error(request, f"No se pudo iniciar la asistencia: {e}")
        return redirect(reverse("interpretation:index"))


def conversation_view(request, context_id):
    context = get_object_or_404(InterpretationContext, id=context_id)
    traces = ConversationTrace.objects.filter(context=context).order_by("created_at")
    return render(
        request,
        "interpretation/conversation.html",
        {
            "context": context,
            "traces": traces,
        },
    )


# === AI-Driven Theme Discovery Views ===


def theme_discovery_view(request, project_id):
    """Main view for theme discovery workflow."""
    project = get_object_or_404(Project, id=project_id)
    step = int(request.GET.get("step", 1))

    context = {
        "project": project,
        "step": step,
    }

    if step == 1:
        # Code Normalization Step
        initial_codes = InitialCode.objects.filter(project=project).order_by("-frequency")
        normalization_proposals = CodeNormalizationProposal.objects.filter(
            project=project
        ).order_by("-created_at")

        context.update(
            {
                "initial_codes": initial_codes,
                "normalization_proposals": normalization_proposals,
            }
        )
    elif step == 2:
        # Theme Generation Step
        normalized_codes = NormalizedCode.objects.filter(project=project).order_by(
            "research_question_focus", "code"
        )
        theme_proposals = ThemeDiscoveryProposal.objects.filter(
            project=project
        ).prefetch_related("codes_used")
        
        # Get created themes from finalized proposals
        finalized_proposals = theme_proposals.filter(created_theme__isnull=False)
        created_themes = [p.created_theme for p in finalized_proposals if p.created_theme]

        context.update(
            {
                "normalized_codes": normalized_codes,
                "theme_proposals": theme_proposals,
                "created_themes": created_themes,
            }
        )

    return render(request, "interpretation/theme_discovery.html", context)


@require_http_methods(["POST"])
def normalize_codes(request, project_id):
    """Trigger AI code normalization."""
    project = get_object_or_404(Project, id=project_id)

    try:
        theme_discovery_service.propose_code_normalization(project)
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@require_http_methods(["POST"])
def accept_normalization(request, proposal_id):
    """Accept or reject a normalization proposal."""
    proposal = get_object_or_404(CodeNormalizationProposal, id=proposal_id)

    try:
        data = json.loads(request.body)
        action = data.get("action", "accept")

        if action == "accept":
            proposal.status = "ACCEPTED"
            proposal.save()
        elif action == "reject":
            proposal.status = "REJECTED"
            proposal.save()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@require_http_methods(["POST"])
def accept_all_normalizations(request, project_id):
    """Accept all pending normalization proposals and create normalized codes."""
    project = get_object_or_404(Project, id=project_id)

    try:
        # Get all accepted or modified proposals
        proposals = CodeNormalizationProposal.objects.filter(
            project=project, status__in=["ACCEPTED", "PENDING"]
        )
        proposal_ids = list(proposals.values_list("id", flat=True))

        # Accept all pending proposals first
        proposals.filter(status="PENDING").update(status="ACCEPTED")

        # Create normalized codes from accepted proposals
        theme_discovery_service.accept_normalization_proposals(
            proposal_ids=proposal_ids, reviewer=request.user
        )
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@require_http_methods(["POST"])
def generate_themes(request, project_id):
    """Trigger AI theme generation."""
    project = get_object_or_404(Project, id=project_id)

    try:
        theme_discovery_service.propose_theme_structure(project)
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@require_http_methods(["POST"])
def accept_theme(request, proposal_id):
    """Accept, reject, or modify a theme proposal."""
    proposal = get_object_or_404(ThemeDiscoveryProposal, id=proposal_id)

    try:
        data = json.loads(request.body)
        action = data.get("action", "accept")

        if action == "accept":
            proposal.status = "ACCEPTED"
            proposal.save()
        elif action == "reject":
            proposal.status = "REJECTED"
            proposal.save()
        elif action == "modify":
            # Track reflexivity when researcher modifies AI suggestion
            new_name = data.get("new_name")
            original_name = data.get("original_name")

            proposal.theme_name = new_name
            proposal.status = "MODIFIED"
            proposal.save()

            # Update rationale to track modification
            if proposal.rationale:
                proposal.rationale += f"\n[Researcher modified: '{original_name}' → '{new_name}']"
            else:
                proposal.rationale = f"[Researcher modified: '{original_name}' → '{new_name}']"
            proposal.save()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@require_http_methods(["POST"])
def accept_all_themes(request, project_id):
    """Accept all pending theme proposals."""
    project = get_object_or_404(Project, id=project_id)

    try:
        proposals = ThemeDiscoveryProposal.objects.filter(
            project=project, status="PENDING"
        )
        proposals.update(status="ACCEPTED")
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@require_http_methods(["POST"])
def finalize_themes(request, project_id):
    """Create actual Theme objects from accepted proposals."""
    project = get_object_or_404(Project, id=project_id)

    try:
        # Get all accepted or modified proposals
        proposals = ThemeDiscoveryProposal.objects.filter(
            project=project, status__in=["ACCEPTED", "MODIFIED"]
        )

        # Create themes from each accepted proposal
        all_created_themes = []
        for proposal in proposals:
            created_themes = theme_discovery_service.accept_and_create_themes(
                proposal_id=proposal.id, reviewer=request.user
            )
            all_created_themes.extend(created_themes)

        return JsonResponse(
            {
                "success": True,
                "created_count": len(all_created_themes),
            }
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
