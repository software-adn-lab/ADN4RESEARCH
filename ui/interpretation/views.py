from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponse
from apps.interpretation.conclusion_assistant.services.interpretation_services import (
    InterpretationService,
)
from apps.interpretation.conclusion_assistant.models import (
    InterpretationContext,
    ConversationTrace,
    InterpretativeProposition,
)
from apps.interpretation.conclusion_assistant.models.subtheme_models import SubTheme
from apps.interpretation.conclusion_assistant.models.theme_models import Theme
from apps.interpretation.structured_data.manager import StructuredDataManager
from apps.interpretation.visualization.engine import ResultsVisualizationEngine
from apps.interpretation.facade import get_interpretation_facade


service = InterpretationService()
# Usamos la fachada para exportación en lugar del servicio directo
interpretation_facade = get_interpretation_facade()


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


@require_http_methods(["POST", "GET"])
def start_theme_interpretation(request, theme_id):
    """Start interpretation directly from a Level 1 Theme (without subtheme)."""
    theme = get_object_or_404(Theme, id=theme_id)

    try:
        subthemes = theme.subthemes.all()

        if subthemes.exists():
            first_subtheme = subthemes.first()
            context, _ = service.initiate_interpretation_context(first_subtheme)
            messages.success(
                request, f"Interpretation started for: {first_subtheme.name}"
            )
        else:
            subtheme = SubTheme.objects.create(
                theme=theme,
                name=theme.name,
                central_codes=[],
                status=SubTheme.Status.IN_PROGRESS,
            )
            context, _ = service.initiate_interpretation_context(subtheme)
            messages.success(request, f"Interpretation started for theme: {theme.name}")

        return redirect(reverse("interpretation:conversation", args=[context.id]))
    except Exception as e:
        messages.error(request, f"Failed to start interpretation: {e}")
        return redirect(reverse("interpretation:index"))


def conversation_view(request, context_id):
    context = get_object_or_404(InterpretationContext, id=context_id)
    traces = ConversationTrace.objects.filter(context=context).order_by("created_at")
    propositions = InterpretativeProposition.objects.filter(
        subtheme=context.subtheme
    ).order_by("-created_at")
    return render(
        request,
        "interpretation/conversation.html",
        {
            "context": context,
            "traces": traces,
            "propositions": propositions,
        },
    )


@require_http_methods(["POST"])
def create_draft(request, context_id):
    """Create a draft interpretative proposition based on researcher instruction."""
    context = get_object_or_404(InterpretationContext, id=context_id)
    instruction = request.POST.get("instruction", "")

    if not instruction:
        messages.error(request, "La instrucción no puede estar vacía.")
        return redirect(reverse("interpretation:conversation", args=[context_id]))

    try:
        service.create_proposition_draft(
            context=context,
            instruction=instruction,
            researcher=request.user if request.user.is_authenticated else None,
        )
        messages.success(request, "Proposición borrador creada exitosamente.")
        return redirect(reverse("interpretation:conversation", args=[context_id]))
    except Exception as e:
        messages.error(request, f"Error al crear proposición: {e}")
        return redirect(reverse("interpretation:conversation", args=[context_id]))


@require_http_methods(["POST"])
def refine_proposition(request, context_id, prop_id):
    """Refine an existing proposition based on new instruction."""
    get_object_or_404(InterpretationContext, id=context_id)
    proposition = get_object_or_404(InterpretativeProposition, id=prop_id)
    refinement = request.POST.get("refinement", "")

    if not refinement:
        messages.error(request, "La instrucción de refinamiento no puede estar vacía.")
        return redirect(reverse("interpretation:conversation", args=[context_id]))

    try:
        service.refine_proposition(
            proposition=proposition,
            refinement_instruction=refinement,
        )
        messages.success(request, "Proposición refinada exitosamente.")
        return redirect(reverse("interpretation:conversation", args=[context_id]))
    except Exception as e:
        messages.error(request, f"Error al refinar proposición: {e}")
        return redirect(reverse("interpretation:conversation", args=[context_id]))


@require_http_methods(["POST"])
def finalize_proposition(request, context_id, prop_id):
    """Finalize a proposition as a final finding."""
    get_object_or_404(InterpretationContext, id=context_id)
    proposition = get_object_or_404(InterpretativeProposition, id=prop_id)

    try:
        finalized = service.finalize_proposition(proposition)
        messages.success(
            request, f"Proposición finalizada como hallazgo: {finalized.id}"
        )
        return redirect(reverse("interpretation:index"))
    except Exception as e:
        messages.error(request, f"Error al finalizar proposición: {e}")
        return redirect(reverse("interpretation:conversation", args=[context_id]))


@require_http_methods(["GET"])
def results_dashboard(request, project_id):
    """
    Displays the interpretation dashboard with visualizations.
    """
    data_manager = StructuredDataManager()
    viz_engine = ResultsVisualizationEngine()

    # Get studies (optionally filtered from query params)
    filters = {}
    if request.GET.get("year_start"):
        try:
            filters["year_start"] = int(request.GET.get("year_start"))
        except ValueError:
            pass
    if request.GET.get("year_end"):
        try:
            filters["year_end"] = int(request.GET.get("year_end"))
        except ValueError:
            pass
    if request.GET.get("source"):
        filters["source"] = request.GET.get("source")

    studies = data_manager.get_studies_for_interpretation(str(project_id), filters)
    dashboard_data = viz_engine.generate_dashboard_data(studies)

    return render(
        request,
        "interpretation/results_dashboard.html",
        {"dashboard_data": dashboard_data, "project_id": project_id},
    )


@require_http_methods(["GET"])
def export_findings(request, project_id):
    """
    Exports findings in the requested format (PDF, CSV, JSON).
    """
    format_type = request.GET.get("format", "pdf")

    try:
        content, mime_type, filename = interpretation_facade.export_findings(
            project_id=str(project_id), export_format=format_type
        )

        response = HttpResponse(
            content.getvalue() if hasattr(content, "getvalue") else content,
            content_type=mime_type,
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        messages.error(request, f"Error exporting findings: {e}")
        return redirect(reverse("interpretation:results_dashboard", args=[project_id]))
