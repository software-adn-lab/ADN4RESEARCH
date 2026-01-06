"""
Views - Taxonomy Bounded Context
Responsabilidad: Gestión del sistema de etiquetas (tags)
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView

from .forms import DeductiveTagForm
from .services import TagDefinitionService
from apps.extraction.planning.models import ExtractionPhase, ExtractionStatusChoices
from apps.extraction.shared.mixins import OwnerRequiredMixin


class TagCreateView(LoginRequiredMixin, OwnerRequiredMixin, CreateView):
    """
    Crear un nuevo tag deductivo.
    
    Usa CreateView genérico de Django en lugar de View manual.
    Referencia: https://docs.djangoproject.com/en/stable/ref/class-based-views/generic-editing/#createview
    """
    
    form_class = DeductiveTagForm
    template_name = None  # No necesitamos template porque redirigimos
    
    def get_form_kwargs(self):
        """
        Pasar el proyecto al formulario.
        Referencia: https://docs.djangoproject.com/en/stable/ref/class-based-views/mixins-editing/#django.views.generic.edit.FormMixin.get_form_kwargs
        """
        kwargs = super().get_form_kwargs()
        
        # Obtener fase desde URL
        phase_id = self.kwargs.get('phase_id') or self.request.POST.get('phase_id')
        phase = get_object_or_404(ExtractionPhase, pk=phase_id)
        
        # Validar que la fase no esté cerrada
        if phase.status == ExtractionStatusChoices.CLOSED:
            messages.error(
                self.request,
                "No se pueden agregar tags en una fase cerrada."
            )
            # Nota: CreateView no maneja bien esto, por eso usamos form_valid
        
        kwargs['project'] = phase.project
        self.phase = phase  # Guardar para usar en form_valid
        
        return kwargs
    
    def form_valid(self, form):
        """
        Procesar formulario válido usando el servicio de dominio.
        Referencia: https://docs.djangoproject.com/en/stable/ref/class-based-views/mixins-editing/#django.views.generic.edit.FormMixin.form_valid
        """
        # Validar estado de la fase
        if self.phase.status == ExtractionStatusChoices.CLOSED:
            messages.error(
                self.request,
                "No se pueden agregar tags en una fase cerrada."
            )
            return redirect(self.get_success_url())
        
        # Usar servicio de dominio
        service = TagDefinitionService()
        
        try:
            tag = service.define_deductive_tag(
                phase_id=self.phase.id,
                name=form.cleaned_data['name'],
                rq_id=form.cleaned_data.get('rq_related').id if form.cleaned_data.get('rq_related') else None,
                user=self.request.user
            )
            
            messages.success(
                self.request,
                f'Tag "{tag.name}" creado exitosamente.'
            )
            
        except Exception as e:
            messages.error(
                self.request,
                f'Error creando tag: {str(e)}'
            )
        
        return redirect(self.get_success_url())
    
    def form_invalid(self, form):
        """
        Manejar errores de validación.
        """
        messages.error(
            self.request,
            'Error en los datos del formulario. Verifica e intenta de nuevo.'
        )
        
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        """
        Redirigir al dashboard con tab de tags.
        """
        return reverse('extraction:phase_detail', kwargs={'pk': self.phase.id}) + '?tab=tags'