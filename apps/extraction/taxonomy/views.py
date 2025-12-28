"""
Bounded Context: Taxonomy
Responsabilidad: Gestión del sistema de etiquetas (tags)
"""
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

# Imports dentro del mismo bounded context
from .services import TagDefinitionService
from .forms import DeductiveTagForm

# Imports de otros bounded contexts
from apps.extraction.planning.models import ExtractionPhase, ExtractionStatusChoices

# Imports del shared kernel
from apps.extraction.shared.mixins import OwnerRequiredMixin


class CreateTagView(LoginRequiredMixin, OwnerRequiredMixin, View):
    """Crea un nuevo tag deductivo."""
    
    def post(self, request, phase_id):
        phase = get_object_or_404(ExtractionPhase, pk=phase_id)

        if phase.status == ExtractionStatusChoices.CLOSED:
            messages.error(
                request, 
                "No se pueden agregar tags en una fase cerrada."
            )
            return redirect('extraction:dashboard', phase_id=phase_id)

        form = DeductiveTagForm(request.POST, project=phase.project)
        if form.is_valid():
            service = TagDefinitionService()
            try:
                service.define_deductive_tag(
                    phase_id=phase.id,
                    name=form.cleaned_data['name'],
                    rq_id=form.cleaned_data['rq_related'].id if form.cleaned_data.get('rq_related') else None,
                    user=request.user
                )
                messages.success(request, "Tag creado exitosamente.")
            except Exception as e:
                messages.error(request, f"Error creando tag: {str(e)}")

        return redirect('extraction:dashboard', phase_id=phase_id)