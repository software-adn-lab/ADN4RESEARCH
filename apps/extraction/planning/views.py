"""
Bounded Context: Planning
Responsabilidad: Gestión del ciclo de vida de fases de extracción
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

# Imports dentro del mismo bounded context
from .models import ExtractionPhase, ExtractionStatusChoices
from .forms import ExtractionPhaseConfigForm
from .services import PhaseLifecycleService

# Imports de otros bounded contexts (Dependency explícita)
from apps.extraction.taxonomy.services import TagDefinitionService
from apps.extraction.taxonomy.forms import DeductiveTagForm
from apps.extraction.core.models import PaperExtraction, Quote

# Imports del shared kernel
from apps.extraction.shared.exceptions import BusinessRuleViolation
from apps.extraction.shared.mixins import OwnerRequiredMixin


class ExtractionDashboardView(LoginRequiredMixin, View):
    """Vista principal del dashboard de extracción."""
    
    template_name = 'dashboard.html'

    def get(self, request, phase_id):
        phase = get_object_or_404(ExtractionPhase, pk=phase_id)
        project = phase.project

        is_owner = (request.user == project.owner)
        is_researcher = not is_owner

        active_tab = request.GET.get('tab', 'studies')
        phase_is_config = phase.status == ExtractionStatusChoices.CONFIG
        is_restricted = is_researcher and phase_is_config

        if is_restricted:
            return render(request, self.template_name, {
                'phase': phase,
                'project': project,
                'is_owner': False,
                'is_restricted': True,
                'active_tab': 'restricted'
            })

        context = {
            'phase': phase,
            'project': project,
            'is_owner': is_owner,
            'active_tab': active_tab,
            'is_restricted': False,
        }

        if is_owner:
            context['config_form'] = ExtractionPhaseConfigForm(instance=phase)
            context['tag_form'] = DeductiveTagForm(project=project)

        if active_tab == 'tags':
            context['tags'] = phase.tags.all().order_by('-created_at')
            
            if is_owner:
                service = PhaseLifecycleService()
                report = service.get_protocol_coverage(phase)
                context['coverage_report'] = report
                context['can_open_phase'] = report.is_fully_covered

        elif active_tab == 'studies':
            if is_researcher:
                papers = PaperExtraction.objects.filter(
                    extraction_phase=phase,
                    assigned_to=request.user
                ).select_related('study')
            else:
                papers = phase.papers_to_extract.all().select_related(
                    'study', 'assigned_to'
                )
            context['papers'] = papers

        elif active_tab == 'quotes':
            quotes_qs = Quote.objects.filter(
                paper_extraction__extraction_phase=phase
            )

            if is_researcher:
                quotes_qs = quotes_qs.filter(created_by=request.user)

            context['quotes'] = quotes_qs.select_related(
                'paper_extraction__study', 
                'created_by'
            ).prefetch_related('tags')

        return render(request, self.template_name, context)


class PhaseConfigUpdateView(LoginRequiredMixin, OwnerRequiredMixin, View):
    """Actualiza la configuración de una fase."""
    
    def post(self, request, phase_id):
        phase = get_object_or_404(ExtractionPhase, pk=phase_id)
        
        if phase.status == ExtractionStatusChoices.CLOSED:
            messages.error(request, "No se puede editar una fase cerrada.")
            return redirect('extraction:dashboard', phase_id=phase_id)

        form = ExtractionPhaseConfigForm(request.POST, instance=phase)
        if form.is_valid():
            form.save()
            messages.success(request, "Configuración actualizada.")
        else:
            messages.error(request, "Error en la configuración.")
        
        return redirect('extraction:dashboard', phase_id=phase_id)


class OpenPhaseView(LoginRequiredMixin, OwnerRequiredMixin, View):
    """Abre una fase de extracción (transición de estado)."""
    
    def post(self, request, phase_id):
        phase = get_object_or_404(ExtractionPhase, pk=phase_id)
        
        service = PhaseLifecycleService()
        try:
            service.attempt_open_phase(phase)
            messages.success(
                request, 
                "¡Fase Abierta! Los investigadores pueden empezar."
            )
        except BusinessRuleViolation as e:
            messages.error(request, str(e))

        return redirect('extraction:dashboard', phase_id=phase_id)