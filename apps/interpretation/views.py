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
    InterpretativeProposition,
)
from apps.interpretation.conclusion_assistant.models.subtheme_models import SubTheme
from apps.interpretation.conclusion_assistant.models.theme_models import Theme


service = InterpretationService()


def index(request):
    """List available themes and subthemes to start interpretation."""
    themes = Theme.objects.all().prefetch_related('subthemes')
    return render(request, 'interpretation/index.html', {'themes': themes})


@require_http_methods(['POST', 'GET'])
def start_interpretation(request, subtheme_id):
    subtheme = get_object_or_404(SubTheme, id=subtheme_id)
    try:
        context, trace = service.initiate_interpretation_context(subtheme)
        messages.success(request, 'Asistencia iniciada.')
        return redirect(reverse('interpretation:conversation', args=[context.id]))
    except Exception as e:
        messages.error(request, f'No se pudo iniciar la asistencia: {e}')
        return redirect(reverse('interpretation:index'))


def conversation_view(request, context_id):
    context = get_object_or_404(InterpretationContext, id=context_id)
    traces = ConversationTrace.objects.filter(context=context).order_by('created_at')
    propositions = InterpretativeProposition.objects.filter(subtheme=context.subtheme).order_by('-modified_at')
    return render(request, 'interpretation/conversation.html', {
        'context': context,
        'traces': traces,
        'propositions': propositions,
    })


@require_http_methods(['POST'])
def create_draft(request, context_id):
    context = get_object_or_404(InterpretationContext, id=context_id)
    instruction = request.POST.get('instruction', '').strip()
    if not instruction:
        messages.error(request, 'Por favor, escribe una instrucción para generar el borrador.')
        return redirect(reverse('interpretation:conversation', args=[context.id]))

    researcher = request.user if request.user.is_authenticated else None
    try:
        proposition = service.create_proposition_draft(context, instruction, researcher=researcher)
        messages.success(request, 'Borrador de proposición generado.')
    except Exception as e:
        messages.error(request, f'Error generando borrador: {e}')

    return redirect(reverse('interpretation:conversation', args=[context.id]))


@require_http_methods(['POST'])
def refine_proposition(request, context_id, prop_id):
    proposition = get_object_or_404(InterpretativeProposition, id=prop_id)
    refinement = request.POST.get('refinement', '').strip()
    if not refinement:
        messages.error(request, 'Por favor, escribe una instrucción de refinamiento.')
        return redirect(reverse('interpretation:conversation', args=[context_id]))

    try:
        service.refine_proposition(proposition, refinement)
        messages.success(request, 'Proposición refinada.')
    except Exception as e:
        messages.error(request, f'Error refinando proposición: {e}')

    return redirect(reverse('interpretation:conversation', args=[context_id]))


@require_http_methods(['POST'])
def finalize_proposition(request, context_id, prop_id):
    proposition = get_object_or_404(InterpretativeProposition, id=prop_id)
    try:
        service.finalize_proposition(proposition)
        messages.success(request, 'Proposición finalizada y guardada como hallazgo final.')
    except Exception as e:
        messages.error(request, f'Error finalizando proposición: {e}')

    return redirect(reverse('interpretation:conversation', args=[context_id]))
