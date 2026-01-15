"""
Views - Planning Bounded Context
"""
import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView, UpdateView, View

from .forms import ExtractionPhaseConfigForm
from .models import ExtractionPhase, ExtractionStatusChoices
from .services import PhaseLifecycleService
from apps.extraction.shared.exceptions import BusinessRuleViolation
from apps.extraction.shared.mixins import OwnerRequiredMixin, ProjectMemberRequiredMixin
from apps.extraction.taxonomy.forms import DeductiveTagForm
from apps.extraction.taxonomy.services import TagApprovalService
from apps.extraction.core.models import PaperExtraction, Quote
from apps.extraction.shared.design_protocol import DesignProtocolAdapter
from apps.extraction.adapters.selection import get_selection_adapter
from apps.extraction.adapters.acquisition import get_acquisition_adapter

logger = logging.getLogger(__name__)


class ExtractionPhaseDetailView(LoginRequiredMixin, ProjectMemberRequiredMixin, DetailView):
    """
    Dashboard principal de una fase de extracción.
    Maneja tabs via query parameter (?tab=...)
    
    La phase se obtiene automáticamente basándose en project_id.
    """
    
    model = ExtractionPhase
    template_name = 'extraction/templates/dashboard.html'
    context_object_name = 'phase'
    
    def get_object(self, queryset=None):
        """
        Obtener la phase basándose en project_id.
        Esto asegura que solo haya una phase por proyecto.
        """
        project_id = self.kwargs.get('project_id')
        return get_object_or_404(
            ExtractionPhase,
            project_id=project_id
        )
    
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
            # Tags con optimización - Solo mostrar deductivos y inductivos aprobados
            all_tags = phase.tags.filter(
                Q(type='DEDUCTIVE') | Q(type='INDUCTIVE', status='APPROVED')
            ).select_related('rq_related').order_by('-created_at')
            
            context['tags'] = all_tags
            adapter = DesignProtocolAdapter()
            context['protocol_questions'] = adapter.get_approved_questions(phase.project_id)
            
            # ✅ Calcular counts por tipo (solo deductivos y inductivos aprobados)
            context['deductive_tags_count'] = all_tags.filter(type='DEDUCTIVE').count()
            context['inductive_tags_count'] = all_tags.filter(type='INDUCTIVE', status='APPROVED').count()
            
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
            
            # Agregar miembros del proyecto para el modal de reasignación
            if is_owner:
                from apps.project.structure.models.project_models import Membership
                members = [
                    {'id': phase.project.owner.id, 'username': phase.project.owner.username}
                ]
                members.extend([
                    {'id': m.user.id, 'username': m.user.username}
                    for m in Membership.objects.filter(project=phase.project).select_related('user')
                ])
                context['team_members'] = members
        
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

        elif tab == 'pending':
            if is_owner:
                # El owner ve todos los tags inductivos pendientes
                service = TagApprovalService()
                context['pending_tags'] = service.get_pending_tags_for_phase(phase.id)
            else:
                # El researcher solo ve sus propios tags inductivos pendientes
                context['pending_tags'] = phase.tags.filter(
                    type='INDUCTIVE',
                    status='PENDING',
                    created_by=self.request.user
                ).select_related('created_by').order_by('-created_at')


class InitializeExtractionPhaseView(LoginRequiredMixin, OwnerRequiredMixin, View):
    """
    Initialize extraction phase from selection results.
    
    Triggered when user clicks "Go to Extraction Phase" button from Selection module.
    
    Workflow:
    1. Create ExtractionPhase in CONFIG status if it doesn't exist
    2. Get approved papers from Selection module via adapter
    3. Create PaperExtraction records for each approved paper
    4. Trigger fulltext downloads via Acquisition adapter (async)
    5. Redirect to extraction dashboard
    """
    
    http_method_names = ['get']
    
    @transaction.atomic
    def get(self, request, project_id):
        """
        Initialize extraction phase and load approved papers.
        """
        from apps.project.structure.models.project_models import Project
        
        try:
            # Get or create extraction phase
            project = get_object_or_404(Project, id=project_id)
            phase, created = ExtractionPhase.objects.get_or_create(
                project_id=project_id,
                defaults={'status': ExtractionStatusChoices.CONFIG}
            )
            
            if created:
                messages.success(
                    request,
                    f'Extraction phase created for "{project.title}". '
                    'You can now configure tags and assign papers to researchers.'
                )
                logger.info(f"[INIT EXTRACTION] Created phase for project {project_id}")
            else:
                logger.info(f"[INIT EXTRACTION] Phase already exists for project {project_id}")
            
            # Get approved papers from selection
            selection_adapter = get_selection_adapter()
            approved_paper_ids = selection_adapter.get_approved_papers(project_id)
            
            if not approved_paper_ids:
                messages.warning(
                    request,
                    'No approved papers found in selection phase. '
                    'Please complete the selection phase first.'
                )
                logger.warning(f"[INIT EXTRACTION] No approved papers for project {project_id}")
                return redirect(
                    reverse('extraction:planning:phase_detail', kwargs={'project_id': project_id})
                )
            
            # Get study data from acquisition
            acquisition_adapter = get_acquisition_adapter()
            all_studies = acquisition_adapter.get_studies_by_project(project_id)
            
            # Map study IDs to study objects
            studies_by_id = {str(s['id']): s for s in all_studies}
            
            # Create PaperExtraction records for approved papers
            created_count = 0
            skipped_count = 0
            
            for paper_id in approved_paper_ids:
                if str(paper_id) not in studies_by_id:
                    logger.warning(f"[INIT EXTRACTION] Study {paper_id} not found in acquisition")
                    skipped_count += 1
                    continue
                
                # Create PaperExtraction if it doesn't exist
                paper_ext, created = PaperExtraction.objects.get_or_create(
                    extraction_phase=phase,
                    study_id=str(paper_id),
                    defaults={'status': 'PENDING'}
                )
                
                if created:
                    created_count += 1
                else:
                    skipped_count += 1
            
            # Trigger fulltext downloads asynchronously
            try:
                download_result = acquisition_adapter.download_fulltexts(
                    approved_paper_ids
                )
                logger.info(
                    f"[INIT EXTRACTION] Download triggered: "
                    f"{download_result['downloaded_count']} completed, "
                    f"{download_result['failed_count']} failed"
                )
            except Exception as e:
                logger.error(
                    f"[INIT EXTRACTION] Failed to trigger downloads: {e}",
                    exc_info=True
                )
                # Don't fail the entire operation if downloads fail
            
            messages.success(
                request,
                f'Loaded {created_count} papers for extraction. '
                f'({skipped_count} were already loaded). '
                'PDFs are being downloaded in the background.'
            )
            logger.info(
                f"[INIT EXTRACTION] Created {created_count} papers, "
                f"skipped {skipped_count} for project {project_id}"
            )
            
        except Exception as e:
            logger.error(
                f"[INIT EXTRACTION] Initialization failed: {e}",
                exc_info=True
            )
            messages.error(
                request,
                f'Failed to initialize extraction phase: {str(e)}'
            )
        
        # Redirect to extraction dashboard
        return redirect(
            reverse('extraction:planning:phase_detail', kwargs={'project_id': project_id})
        )


class PhaseConfigUpdateView(LoginRequiredMixin, ProjectMemberRequiredMixin, OwnerRequiredMixin, UpdateView):
    """
    Actualizar configuración de una fase.
    Usa UpdateView genérico de Django.
    
    La phase se obtiene automáticamente basándose en project_id.
    
    Referencia: https://docs.djangoproject.com/en/stable/ref/class-based-views/generic-editing/#updateview
    """
    
    model = ExtractionPhase
    form_class = ExtractionPhaseConfigForm
    
    def get_object(self, queryset=None):
        """Obtener la phase basándose en project_id."""
        project_id = self.kwargs.get('project_id')
        return get_object_or_404(
            ExtractionPhase,
            project_id=project_id
        )
    
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
        return reverse('extraction:planning:phase_detail', kwargs={
            'project_id': self.object.project_id
        })


class PhaseOpenView(LoginRequiredMixin, ProjectMemberRequiredMixin, OwnerRequiredMixin, View):
    """
    Transición de estado: CONFIG -> OPEN
    
    Business Rules:
    - Solo el owner puede abrir una fase
    - La fase debe estar en estado CONFIG
    - Todas las RQs del protocolo deben estar cubiertas por tags deductivos aprobados
    
    La phase se obtiene automáticamente basándose en project_id.
    
    Referencia: https://docs.djangoproject.com/en/stable/ref/class-based-views/base/#view
    """
    
    def post(self, request, project_id):
        """
        Procesar solicitud de apertura de fase.
        
        Args:
            request: HTTP request
            project_id: ID del proyecto (la phase se obtiene automáticamente)
            
        Returns:
            Redirect al dashboard de la fase
        """
        phase = get_object_or_404(ExtractionPhase, project_id=project_id)
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
        return redirect(f"{reverse('extraction:planning:phase_detail', kwargs={'project_id': project_id})}?tab=tags")
