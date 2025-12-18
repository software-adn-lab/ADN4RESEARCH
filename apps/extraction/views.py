# apps/extraction/planning/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.views.generic import DetailView

# Imports Absolutos (Best Practice)
from apps.extraction.planning.models import ExtractionPhase, ExtractionStatusChoices
from apps.extraction.planning.forms import ExtractionPhaseConfigForm, DeductiveTagForm
from apps.extraction.planning.services import PhaseLifecycleService
from apps.extraction.taxonomy.services import TagDefinitionService
from apps.extraction.core.models import PaperExtraction, Quote
from apps.extraction.shared.exceptions import BusinessRuleViolation


class OwnerRequiredMixin(UserPassesTestMixin):
    """Mixin para asegurar que solo el staff/owner pueda ejecutar acciones de escritura."""

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser


class ExtractionDashboardView(LoginRequiredMixin, View):

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
                papers = phase.papers_to_extract.all().select_related('study', 'assigned_to')
            context['papers'] = papers

        elif active_tab == 'quotes':
            quotes_qs = Quote.objects.filter(paper_extraction__extraction_phase=phase)

            if is_researcher:
                quotes_qs = quotes_qs.filter(created_by=request.user)

            context['quotes'] = quotes_qs.select_related(
                'paper_extraction__study', 
                'created_by'
            ).prefetch_related('tags')

        return render(request, self.template_name, context)

# --- Action Views (Protegidas con OwnerRequiredMixin) ---

class PhaseConfigUpdateView(LoginRequiredMixin, OwnerRequiredMixin, View):
    def post(self, request, phase_id):
        phase = get_object_or_404(ExtractionPhase, pk=phase_id)
        # Doble chequeo de seguridad: No se puede configurar si está cerrada (opcional)
        if phase.status == ExtractionStatusChoices.CLOSED:
            messages.error(request, "No se puede editar una fase cerrada.")
            return redirect(f"/extraction/{phase_id}/?tab=config")

        form = ExtractionPhaseConfigForm(request.POST, instance=phase)
        if form.is_valid():
            form.save()
            messages.success(request, "Configuración actualizada.")
        else:
            messages.error(request, "Error en la configuración.")
        return redirect(f"/extraction/{phase_id}/?tab=config")


class CreateTagView(LoginRequiredMixin, OwnerRequiredMixin, View):
    def post(self, request, phase_id):
        phase = get_object_or_404(ExtractionPhase, pk=phase_id)

        if phase.status == ExtractionStatusChoices.CLOSED:
            messages.error(request, "No se pueden agregar tags en una fase cerrada.")
            return redirect(f"/extraction/{phase_id}/?tab=tags")

        form = DeductiveTagForm(request.POST, project=phase.project)
        if form.is_valid():
            service = TagDefinitionService()
            try:
                service.define_deductive_tag(
                    phase_id=phase.id,
                    name=form.cleaned_data['name'],
                    rq_id=form.cleaned_data['rq_related'].id if form.cleaned_data['rq_related'] else None,
                    user=request.user
                )
                messages.success(request, "Tag creado exitosamente.")
            except Exception as e:
                messages.error(request, f"Error creando tag: {str(e)}")

        return redirect(f"/extraction/{phase_id}/?tab=tags")


class OpenPhaseView(LoginRequiredMixin, OwnerRequiredMixin, View):
    def post(self, request, phase_id):
        # 1. Obtenemos el objeto completo aquí
        phase = get_object_or_404(ExtractionPhase, pk=phase_id)
        
        service = PhaseLifecycleService()
        try:
            # 2. Pasamos el objeto 'phase', no el 'phase_id'
            service.attempt_open_phase(phase)
            messages.success(request, "¡Fase Abierta! Los investigadores pueden empezar.")
        except BusinessRuleViolation as e:
            messages.error(request, str(e))

        return redirect(f"/extraction/{phase_id}/?tab=tags")

class PaperExtractionDetailView(LoginRequiredMixin, DetailView):
    model = PaperExtraction
    template_name = 'paper_extraction_detail.html'
    context_object_name = 'paper'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['available_tags'] = self.object.extraction_phase.tags.filter(status='APPROVED')
        return context