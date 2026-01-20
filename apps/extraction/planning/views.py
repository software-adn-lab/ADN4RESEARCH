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
from apps.extraction.core.models import PaperExtraction, Quote, PaperExtractionStatusChoices
from apps.extraction.adapters.selection import get_selection_adapter
from apps.extraction.adapters.acquisition import get_acquisition_adapter
from apps.interpretation.conclusion_assistant.models import InterpretationPhase
from apps.extraction.taxonomy.models import Tag, ApprovalStatusChoices
from apps.interpretation.conclusion_assistant.models.normalization_models import InitialCode

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
            
            # Obtener preguntas del protocolo a través de services
            service = PhaseLifecycleService()
            context['protocol_questions'] = service.get_protocol_questions_for_display(phase.project_id)
            
            # ✅ Calcular counts por tipo (solo deductivos y inductivos aprobados)
            context['deductive_tags_count'] = all_tags.filter(type='DEDUCTIVE').count()
            context['inductive_tags_count'] = all_tags.filter(type='INDUCTIVE', status='APPROVED').count()
            
            if is_owner:
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
                from apps.extraction.adapters.project import get_project_adapter
                adapter = get_project_adapter()
                context['team_members'] = adapter.get_project_members(phase.project_id)
        
        elif tab == 'quotes':
            quotes_qs = Quote.objects.filter(
                paper_extraction__extraction_phase=phase
            ).order_by('-created_at')

            if is_researcher:
                quotes_qs = quotes_qs.filter(created_by=self.request.user)
            
            from django.core.paginator import Paginator
            paginator = Paginator(quotes_qs.select_related(
                'paper_extraction__study',
                'created_by'
            ).prefetch_related('tags'), 10)

            page_number = self.request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            
            context['quotes_page'] = page_obj
            context['quotes_count'] = paginator.count

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
            selection_adapter = get_selection_adapter()
            if not selection_adapter.is_selection_complete(project_id):
                messages.warning(
                    request,
                    'Selection phase is not complete yet. Resolve discussions and finalize full-text before extraction.'
                )
                return redirect(
                    reverse('selection:fulltext_overview', kwargs={'project_id': project_id})
                )

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

            # Mark selection phase as inactive once extraction starts
            try:
                from apps.selection.features.distribution.models import SelectionPhase
                selection_phase = SelectionPhase.objects.filter(project_id=project_id).first()
                if selection_phase and selection_phase.is_active:
                    selection_phase.is_active = False
                    selection_phase.save(update_fields=['is_active'])
            except Exception:
                pass
            
            acquisition_adapter = get_acquisition_adapter()
            created_count = 0
            skipped_count = 0
            paper_ext_map = {}  # Map paper_id -> PaperExtraction instance

            for paper_id in approved_paper_ids:
                pdf_url = acquisition_adapter.get_study_pdf_url(
                    str(paper_id), project_id=project_id
                )

                paper_ext, created = PaperExtraction.objects.get_or_create(
                    extraction_phase=phase,
                    study_id=str(paper_id),
                    defaults={
                        'status': PaperExtractionStatusChoices.PENDING,
                        'path': pdf_url
                    }
                )

                paper_ext_map[str(paper_id)] = paper_ext
                
                if created:
                    created_count += 1
                else:
                    skipped_count += 1
            
            # Distribute papers among researchers
            try:
                from .services import ApprovedPaperDistributionService
                from django.contrib.auth.models import User
                
                distribution_service = ApprovedPaperDistributionService(project_id)
                distribution = distribution_service.distribute_approved_papers(
                    approved_paper_ids
                )
                
                # Apply distribution: assign papers to researchers
                assignment_count = 0
                for user_id, paper_ids in distribution.items():
                    user = User.objects.get(id=user_id)
                    
                    for paper_id in paper_ids:
                        if str(paper_id) in paper_ext_map:
                            paper_ext = paper_ext_map[str(paper_id)]
                            # Only assign if not already assigned
                            if not paper_ext.assigned_to:
                                paper_ext.assigned_to = user
                                paper_ext.save()
                                assignment_count += 1
                                logger.info(
                                    f"[INIT EXTRACTION] Assigned paper {paper_id} to {user.username}"
                                )
                
                messages.success(
                    request,
                    f'Loaded {created_count} papers and distributed {assignment_count} assignments. '
                    f'({skipped_count} were already loaded).'
                )
                logger.info(
                    f"[INIT EXTRACTION] Created {created_count} papers, "
                    f"assigned {assignment_count}, skipped {skipped_count} for project {project_id}"
                )
                
            except (ValueError, Exception) as e:
                # If distribution fails, still show success for paper loading
                logger.warning(
                    f"[INIT EXTRACTION] Could not distribute papers: {e}"
                )
                messages.warning(
                    request,
                    f'Loaded {created_count} papers, but distribution failed: {str(e)}. '
                    f'You can manually assign papers to researchers.'
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

class StartInterpretationView(LoginRequiredMixin, OwnerRequiredMixin, View):
    """
    Transition from Extraction to Interpretation phase.
    """

    def post(self, request, *args, **kwargs):
        project_id = self.kwargs.get('project_id')
        extraction_phase = get_object_or_404(ExtractionPhase, project_id=project_id)
        
        # Get or Create Interpretation Phase
        interp_phase, created = InterpretationPhase.objects.get_or_create(
            project=extraction_phase.project,
            defaults={'is_active': False}
        )
        
        # Activate it
        interp_phase.is_active = True
        interp_phase.save()
        
        # --- POPULATE INITIAL CODES FROM EXTRACTION TAGS ---
        # 1. Fetch all APPROVED tags from the extraction phase
        tags = Tag.objects.filter(
            extraction_phase=extraction_phase,
            status=ApprovalStatusChoices.APPROVED
        )
        
        for tag in tags:
            # Check how many times this tag was used in quotes
            # Assuming Quote has a ManyToManyField 'tags'
            usage_count = Quote.objects.filter(tags=tag).count()
            
            # Create or Update InitialCode in Interpretation
            # We map Tag.name -> InitialCode.code_name
            InitialCode.objects.update_or_create(
                project=extraction_phase.project,
                code=tag.name,  # Mapping name to code
                defaults={
                    'frequency': usage_count,
                }
            )
        
        messages.success(request, f"Interpretation Phase activated. {tags.count()} tags have been loaded as initial codes.")
        
        # Redirect to Interpretation Theme Discovery (step 1)
        return redirect(f"{reverse('interpretation:theme_discovery', args=[project_id])}?step=1")
