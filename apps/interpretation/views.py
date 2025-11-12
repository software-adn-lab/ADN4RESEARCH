from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.contrib import messages

from apps.interpretation.conclusion_assistant.services.interpretation_services import (
    InterpretationService,
)
from apps.interpretation.conclusion_assistant.models import (
    InterpretationContext,
    ConversationTrace,
    # InterpretativeProposition,  # Used in Scenario 2 - currently commented out
)
from apps.interpretation.conclusion_assistant.models.subtheme_models import SubTheme
from apps.interpretation.conclusion_assistant.models.theme_models import Theme


service = InterpretationService()


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
