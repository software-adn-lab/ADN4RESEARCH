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
        """
        Cargar datos específicos del tab activo (lazy loading).
        """
        
        if tab == 'tags':
            # Tags con optimización
            all_tags = phase.tags.all().select_related('rq_related').order_by('-created_at')
            context['tags'] = all_tags
            
            # ✅ Calcular counts por tipo
            context['deductive_tags_count'] = all_tags.filter(type='DEDUCTIVE').count()
            context['inductive_tags_count'] = all_tags.filter(type='INDUCTIVE').count()
            
            if is_owner:
                service = PhaseLifecycleService()
                coverage_report = service.get_protocol_coverage(phase)
                context['coverage_report'] = coverage_report
                context['can_open_phase'] = coverage_report.is_fully_covered
        
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
    
    Referencia: https://docs.djangoproject.com/en/stable/ref/class-based-views/generic-editing/#updateview
    """
    
    model = ExtractionPhase
    form_class = ExtractionPhaseConfigForm
    
    def form_valid(self, form):
        """
        Validar estado antes de guardar.
        
        Business Rules:
        - No se puede editar una fase CLOSED
        """
        if self.object.status == ExtractionStatusChoices.CLOSED:
            messages.error(self.request, "No se puede editar una fase cerrada.")
            return redirect(self.get_success_url())
        
        messages.success(self.request, "Configuración actualizada exitosamente.")
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirigir al dashboard de la fase después de guardar."""
        return reverse('extraction:phase_detail', args=[self.object.pk])


class PhaseOpenView(LoginRequiredMixin, OwnerRequiredMixin, View):
    """
    Transición de estado: CONFIG -> OPEN
    
    Business Rules:
    - Solo el owner puede abrir una fase
    - La fase debe estar en estado CONFIG
    - Todas las RQs del protocolo deben estar cubiertas por tags deductivos aprobados
    
    Referencia: https://docs.djangoproject.com/en/stable/ref/class-based-views/base/#view
    """
    
    def post(self, request, pk):
        """
        Procesar solicitud de apertura de fase.
        
        Args:
            request: HTTP request
            pk: ID de la fase a abrir
            
        Returns:
            Redirect al dashboard de la fase
        """
        phase = get_object_or_404(ExtractionPhase, pk=pk)
        service = PhaseLifecycleService()
        
        try:
            # ✅ Intentar abrir la fase (valida cobertura automáticamente)
            service.attempt_open_phase(phase)
            
            messages.success(
                request,
                "✅ ¡Fase Abierta! Los investigadores pueden comenzar la extracción."
            )
            
        except BusinessRuleViolation as e:
            # ✅ Capturar error de negocio y mostrar mensaje
            messages.error(request, str(e))
        
        # ✅ Redirigir al tab de tags para ver el estado
        return redirect(f"{reverse('extraction:phase_detail', args=[pk])}?tab=tags")
