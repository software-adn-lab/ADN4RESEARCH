"""
Views - Planning Bounded Context
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView, UpdateView, View

from .forms import ExtractionPhaseConfigForm
from .models import ExtractionPhase, ExtractionStatusChoices
from .services import PhaseLifecycleService
from apps.extraction.shared.exceptions import BusinessRuleViolation
from apps.extraction.shared.mixins import OwnerRequiredMixin
from apps.extraction.taxonomy.forms import DeductiveTagForm
from apps.extraction.core.models import PaperExtraction, Quote


class ExtractionPhaseDetailView(LoginRequiredMixin, DetailView):
    """
    Dashboard principal de una fase de extracción.
    Maneja tabs via query parameter (?tab=...)
    """
    
    model = ExtractionPhase
    template_name = 'dashboard.html'
    context_object_name = 'phase'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        phase = self.object
        user = self.request.user
        
        # Permisos
        is_owner = user == phase.project.owner
        is_researcher = not is_owner
        
        # Tab activo
        active_tab = self.request.GET.get('tab', 'studies')
        
        # Restringir acceso en CONFIG
        if is_researcher and phase.status == ExtractionStatusChoices.CONFIG:
            context.update({
                'is_restricted': True,
                'is_owner': False,
                'active_tab': 'restricted',
                'project': phase.project
            })
            return context
        
        # Contexto base
        context.update({
            'project': phase.project,
            'is_owner': is_owner,
            'active_tab': active_tab,
            'is_restricted': False,
        })
        
        # Formularios (solo owner)
        if is_owner:
            context['config_form'] = ExtractionPhaseConfigForm(instance=phase)
            context['tag_form'] = DeductiveTagForm(project=phase.project)
        
        # Cargar datos según tab
        self._load_tab_data(context, phase, active_tab, is_owner, is_researcher)
        
        return context
    
    def _load_tab_data(self, context, phase, tab, is_owner, is_researcher):
        """Cargar datos específicos del tab activo (lazy loading)."""
        
        if tab == 'tags':
            context['tags'] = phase.tags.all().order_by('-created_at')
            
            if is_owner:
                service = PhaseLifecycleService()
                report = service.get_protocol_coverage(phase)
                context['coverage_report'] = report
                context['can_open_phase'] = report.is_fully_covered
        
        elif tab == 'studies':
            papers_qs = PaperExtraction.objects.filter(extraction_phase=phase)
            
            if is_researcher:
                papers_qs = papers_qs.filter(assigned_to=self.request.user)
            
            context['papers'] = papers_qs.select_related('study', 'assigned_to')
        
        elif tab == 'quotes':
            quotes_qs = Quote.objects.filter(
                paper_extraction__extraction_phase=phase
            )
            
            if is_researcher:
                quotes_qs = quotes_qs.filter(created_by=self.request.user)
            
            context['quotes'] = quotes_qs.select_related(
                'paper_extraction__study',
                'created_by'
            ).prefetch_related('tags')


class PhaseConfigUpdateView(LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
    """
    Actualizar configuración de una fase.
    Usa UpdateView genérico de Django.
    """
    
    model = ExtractionPhase
    form_class = ExtractionPhaseConfigForm
    
    def form_valid(self, form):
        """Validar estado antes de guardar."""
        if self.object.status == ExtractionStatusChoices.CLOSED:
            messages.error(self.request, "No se puede editar una fase cerrada.")
            return redirect(self.get_success_url())
        
        messages.success(self.request, "Configuración actualizada.")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('extraction:phase_detail', args=[self.object.pk])


class PhaseOpenView(LoginRequiredMixin, OwnerRequiredMixin, View):
    """
    Transición de estado: CONFIG -> OPEN
    """
    
    def post(self, request, pk):
        phase = get_object_or_404(ExtractionPhase, pk=pk)
        service = PhaseLifecycleService()
        
        try:
            service.attempt_open_phase(phase)
            messages.success(
                request,
                "¡Fase Abierta! Los investigadores pueden empezar."
            )
        except BusinessRuleViolation as e:
            messages.error(request, str(e))
        
        return redirect('extraction:phase_detail', pk=pk)