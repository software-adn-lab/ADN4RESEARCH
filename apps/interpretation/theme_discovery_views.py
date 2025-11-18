"""Views for AI-Driven Theme Discovery feature."""
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
import json

from apps.interpretation.conclusion_assistant.services.theme_discovery_services import (
    ThemeDiscoveryService,
)
from apps.interpretation.conclusion_assistant.models.code_models import (
    InitialCode,
    CodeNormalizationProposal,
    NormalizedCode,
    ThemeDiscoveryProposal,
)
from apps.interpretation.conclusion_assistant.models.theme_models import Theme
from apps.project.models import Project


theme_discovery_service = ThemeDiscoveryService()


@login_required
@ensure_csrf_cookie
def theme_discovery_view(request, project_id):
    """Display theme discovery workflow."""
    project = get_object_or_404(Project, id=project_id)
    step = int(request.GET.get("step", 1))

    context = {
        "project": project,
        "step": step,
    }

    if step == 1:
        # Code Normalization Step
        initial_codes = InitialCode.objects.filter(project=project).order_by(
            "-frequency"
        )
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

        # Get created themes - themes are created when proposals are accepted/modified
        # Since Theme doesn't have a FK to proposal, we get themes by created_by user
        created_themes = Theme.objects.filter(
            created_by=request.user
        ).order_by("-created_at")

        context.update(
            {
                "normalized_codes": normalized_codes,
                "theme_proposals": theme_proposals,
                "created_themes": created_themes,
            }
        )

    return render(request, "interpretation/theme_discovery.html", context)


@require_http_methods(["POST"])
@login_required
def normalize_codes(request, project_id):
    """Trigger AI code normalization."""
    project = get_object_or_404(Project, id=project_id)

    try:
        print(f"[DEBUG] Normalizing codes for project {project_id}, user: {request.user}")
        theme_discovery_service.propose_code_normalization(project)
        return JsonResponse({"success": True})
    except Exception as e:
        print(f"[ERROR] Failed to normalize codes: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@require_http_methods(["POST"])
@login_required
def create_manual_normalization(request, project_id):
    """Create a manual normalization proposal."""
    project = get_object_or_404(Project, id=project_id)

    try:
        data = json.loads(request.body)
        normalized_code = data.get("normalized_code", "").strip()
        original_codes = data.get("original_codes", [])
        rationale = data.get("rationale", "").strip()

        if not normalized_code or not original_codes or not rationale:
            return JsonResponse(
                {"success": False, "error": "Missing required fields"}, status=400
            )

        # Create manual normalization proposal
        proposal = CodeNormalizationProposal.objects.create(
            normalized_code=normalized_code,
            original_codes=original_codes,
            rationale=rationale,
            project=project,
            status=CodeNormalizationProposal.ProposalStatus.PENDING,
            created_by_ai=False,  # Mark as manual creation
            reviewed_by=request.user,
        )

        return JsonResponse({"success": True, "proposal_id": proposal.id})
    except Exception as e:
        print(f"[ERROR] Failed to create manual normalization: {e}")
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
        print(f"[DEBUG] Accept all normalizations for project {project_id}")
        
        # Get all accepted or modified proposals
        proposals = CodeNormalizationProposal.objects.filter(
            project=project, status__in=["ACCEPTED", "PENDING"]
        )
        proposal_ids = list(proposals.values_list("id", flat=True))
        print(f"[DEBUG] Found {len(proposal_ids)} proposals to process: {proposal_ids}")

        # Accept all pending proposals first
        pending_count = proposals.filter(status="PENDING").update(status="ACCEPTED")
        print(f"[DEBUG] Marked {pending_count} proposals as ACCEPTED")

        # Create normalized codes from accepted proposals
        print(f"[DEBUG] Creating normalized codes from proposals: {proposal_ids}")
        normalized_codes = theme_discovery_service.accept_normalization_proposals(
            proposal_ids=proposal_ids, reviewer=request.user
        )
        print(f"[DEBUG] Created {len(normalized_codes)} normalized codes")
        
        return JsonResponse({"success": True, "created_count": len(normalized_codes)})
    except Exception as e:
        print(f"[ERROR] Failed to accept normalizations: {e}")
        import traceback
        traceback.print_exc()
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
@login_required
def create_manual_theme(request, project_id):
    """Create a manual theme proposal."""
    project = get_object_or_404(Project, id=project_id)

    try:
        data = json.loads(request.body)
        theme_name = data.get("theme_name", "").strip()
        theme_description = data.get("theme_description", "").strip()
        research_question_focus = data.get("research_question_focus", "").strip()
        code_ids = data.get("code_ids", [])
        rationale = data.get("rationale", "").strip()

        if not theme_name or not theme_description or not research_question_focus or not code_ids or not rationale:
            return JsonResponse(
                {"success": False, "error": "Missing required fields"}, status=400
            )

        # Create manual theme proposal
        proposal = ThemeDiscoveryProposal.objects.create(
            theme_name=theme_name,
            theme_description=theme_description,
            research_question_focus=research_question_focus,
            rationale=rationale,
            project=project,
            status=ThemeDiscoveryProposal.ProposalStatus.PENDING,
            created_by_ai=False,  # Mark as manual creation
            reviewed_by=request.user,
        )

        # Link the selected codes to the proposal
        codes = NormalizedCode.objects.filter(id__in=code_ids, project=project)
        proposal.codes_used.set(codes)

        return JsonResponse({"success": True, "proposal_id": proposal.id})
    except Exception as e:
        print(f"[ERROR] Failed to create manual theme: {e}")
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
                proposal.rationale += (
                    f"\n[Researcher modified: '{original_name}' → '{new_name}']"
                )
            else:
                proposal.rationale = (
                    f"[Researcher modified: '{original_name}' → '{new_name}']"
                )
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
