"""
Views - Taxonomy Bounded Context
Responsabilidad: Gestión del sistema de etiquetas (tags)

Vistas basadas en clases (CBV) siguiendo el patrón MVT de Django.

Referencia Django CBV:
https://docs.djangoproject.com/en/stable/topics/class-based-views/
https://docs.djangoproject.com/en/stable/ref/class-based-views/
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from .forms import DeductiveTagForm, InductiveTagForm, TagApprovalForm, TagFilterForm
from .services import TagDefinitionService, TagApprovalService, TagUsageService
from .models import Tag, TagTypeChoices, ApprovalStatusChoices

# Importar modelos de otros bounded contexts
from apps.extraction.planning.models import ExtractionPhase, ExtractionStatusChoices
from apps.extraction.shared.mixins import OwnerRequiredMixin, ProjectMemberRequiredMixin


# =============================================================================
# VISTAS DE CREACIÓN DE TAGS
# =============================================================================

class TagCreateView(LoginRequiredMixin, ProjectMemberRequiredMixin, OwnerRequiredMixin, CreateView):
    """
    Crear un nuevo tag deductivo.
    
    Usa CreateView genérico de Django.
    La phase se obtiene automáticamente basándose en project_id.
    
    Referencia: 
    https://docs.djangoproject.com/en/stable/ref/class-based-views/generic-editing/#createview
    """
    
    form_class = DeductiveTagForm
    template_name = None  # No necesitamos template porque redirigimos
    
    def get_form_kwargs(self):
        """
        Pasar el proyecto al formulario.
        
        Referencia: 
        https://docs.djangoproject.com/en/stable/ref/class-based-views/mixins-editing/#django.views.generic.edit.FormMixin.get_form_kwargs
        """
        kwargs = super().get_form_kwargs()
        
        project_id = self.kwargs.get('project_id')
        phase = get_object_or_404(ExtractionPhase, project_id=project_id)
        
        if phase.status == ExtractionStatusChoices.CLOSED:
            messages.error(
                self.request,
                "No se pueden agregar tags en una fase cerrada."
            )
        
        kwargs['project'] = phase.project
        self.phase = phase
        
        return kwargs
    
    def form_valid(self, form):
        """
        Procesar formulario válido usando el servicio de dominio.
        
        Referencia: 
        https://docs.djangoproject.com/en/stable/ref/class-based-views/mixins-editing/#django.views.generic.edit.FormMixin.form_valid
        """
        if self.phase.status == ExtractionStatusChoices.CLOSED:
            messages.error(
                self.request,
                "No se pueden agregar tags en una fase cerrada."
            )
            return redirect(self.get_success_url())
        
        service = TagDefinitionService()
        
        try:
            tag = service.define_deductive_tag(
                phase_id=self.phase.id,
                name=form.cleaned_data['name'],
                color=form.cleaned_data.get('color'),
                rq_id=(
                    form.cleaned_data.get('rq_related').id 
                    if form.cleaned_data.get('rq_related') 
                    else None
                ),
                user=self.request.user
            )
            
            messages.success(
                self.request,
                f'Tag deductivo "{tag.name}" creado exitosamente.'
            )
            
        except Exception as e:
            messages.error(
                self.request,
                f'Error creando tag: {str(e)}'
            )
        
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            'extraction:planning:phase_detail',
            kwargs={
                'project_id': self.phase.project_id
            }
        ) + '?tab=tags'


class TagUpdateView(LoginRequiredMixin, ProjectMemberRequiredMixin, OwnerRequiredMixin, UpdateView):
    """
    Actualizar un tag existente.
    """

    model = Tag
    form_class = DeductiveTagForm
    template_name = None

    def get_object(self, queryset=None):
        project_id = self.kwargs.get('project_id')
        phase = get_object_or_404(ExtractionPhase, project_id=project_id)
        self.phase = phase
        return get_object_or_404(Tag, pk=self.kwargs.get('pk'), extraction_phase=phase)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project'] = self.phase.project
        return kwargs

    def form_valid(self, form):
        if self.phase.status == ExtractionStatusChoices.CLOSED:
            messages.error(
                self.request,
                "No se pueden editar tags en una fase cerrada."
            )
            return redirect(self.get_success_url())

        tag = form.save(commit=False)
        tag.is_mandatory = bool(tag.rq_related_id)
        tag.save(update_fields=['name', 'color', 'rq_related', 'is_mandatory', 'updated_at'])

        messages.success(
            self.request,
            f'Tag "{tag.name}" actualizado exitosamente.'
        )
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(
            self.request,
            'Error en los datos del formulario. Verifica e intenta de nuevo.'
        )
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            'extraction:planning:phase_detail',
            kwargs={
                'project_id': self.phase.project_id
            }
        ) + '?tab=tags'


class TagDeleteView(LoginRequiredMixin, ProjectMemberRequiredMixin, OwnerRequiredMixin, View):
    """
    Eliminar un tag existente.
    """

    http_method_names = ['post']

    def post(self, request, project_id, pk):
        phase = get_object_or_404(ExtractionPhase, project_id=project_id)
        tag = get_object_or_404(Tag, pk=pk, extraction_phase=phase)

        if phase.status == ExtractionStatusChoices.CLOSED:
            messages.error(
                request,
                "No se pueden eliminar tags en una fase cerrada."
            )
            return redirect(self.get_success_url(phase))

        tag_name = tag.name
        tag.delete()
        messages.success(request, f'Tag "{tag_name}" eliminado.')
        return redirect(self.get_success_url(phase))

    def get_success_url(self, phase):
        return reverse(
            'extraction:planning:phase_detail',
            kwargs={
                'project_id': phase.project_id
            }
        ) + '?tab=tags'


class InductiveTagCreateView(LoginRequiredMixin, ProjectMemberRequiredMixin, CreateView):
    """
    Crear un nuevo tag inductivo durante la extracción.
    
    Los tags inductivos:
    - Se crean con estado PENDING
    - Tienen visibilidad PRIVATE inicialmente
    - Solo el creador puede usarlos hasta que sean aprobados
    
    La phase se obtiene automáticamente basándose en project_id.
    
    Esta vista puede ser usada desde:
    1. El formulario de creación de Quote (inline)
    2. Un modal/formulario independiente
    
    Referencia:
    https://docs.djangoproject.com/en/stable/ref/class-based-views/generic-editing/#createview
    """
    
    form_class = InductiveTagForm
    template_name = 'taxonomy/inductive_tag_form.html'
    
    def setup(self, request, *args, **kwargs):
        """
        Configuración inicial de la vista.
        Carga la fase de extracción antes de procesar.
        
        Referencia:
        https://docs.djangoproject.com/en/stable/ref/class-based-views/base/#django.views.generic.base.View.setup
        """
        super().setup(request, *args, **kwargs)
        
        project_id = self.kwargs.get('project_id')
        self.phase = get_object_or_404(
            ExtractionPhase.objects.select_related('project'),
            project_id=project_id
        )
    
    def get_form_kwargs(self):
        """Pasar fase y usuario al formulario."""
        kwargs = super().get_form_kwargs()
        kwargs['phase'] = self.phase
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        """
        Agregar contexto adicional al template.
        
        Referencia:
        https://docs.djangoproject.com/en/stable/ref/class-based-views/mixins-simple/#django.views.generic.base.ContextMixin.get_context_data
        """
        context = super().get_context_data(**kwargs)
        context['phase'] = self.phase
        context['project'] = self.phase.project
        return context
    
    def form_valid(self, form):
        """
        Procesar formulario válido usando el servicio de dominio.
        """
        # Validar que la fase no esté cerrada
        if self.phase.status == ExtractionStatusChoices.CLOSED:
            messages.error(
                self.request,
                "No se pueden crear tags en una fase cerrada."
            )
            return redirect(self.get_success_url())
        
        service = TagDefinitionService()
        
        try:
            tag = service.define_inductive_tag(
                phase_id=self.phase.id,
                name=form.cleaned_data['name'],
                user=self.request.user,
                color=form.cleaned_data.get('color')
            )
            
            messages.success(
                self.request,
                f'Tag inductivo "{tag.name}" creado. '
                f'Está pendiente de aprobación pero puedes usarlo en tus extracciones.'
            )
            
            # Si es una petición AJAX, devolver JSON
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'tag': {
                        'id': tag.id,
                        'name': tag.name,
                        'color': tag.color,
                        'type': tag.type,
                        'status': tag.status,
                    },
                    'message': f'Tag "{tag.name}" creado exitosamente.'
                })
            
        except Exception as e:
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=400)
            
            messages.error(
                self.request,
                f'Error creando tag inductivo: {str(e)}'
            )
        
        return redirect(self.get_success_url())
    
    def form_invalid(self, form):
        """Manejar errores de validación."""
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
        
        # Para peticiones normales, re-renderizar el formulario
        return super().form_invalid(form)
    
    def get_success_url(self):
        """URL de redirección tras crear el tag."""
        # Permitir URL personalizada via query param
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        
        return reverse(
            'extraction:planning:phase_detail',
            kwargs={
                'project_id': self.phase.project_id,
                'pk': self.phase.id
            }
        ) + '?tab=tags'


# =============================================================================
# VISTAS DE LISTADO Y FILTRADO
# =============================================================================

class TagListView(LoginRequiredMixin, ProjectMemberRequiredMixin, ListView):
    """
    Listar todos los tags de una fase con filtros.
    
    La phase se obtiene automáticamente basándose en project_id.
    Muestra tags agrupados por tipo y estado.
    
    Referencia:
    https://docs.djangoproject.com/en/stable/ref/class-based-views/generic-display/#listview
    """
    
    model = Tag
    template_name = 'taxonomy/tag_list.html'
    context_object_name = 'tags'
    paginate_by = 20
    
    def setup(self, request, *args, **kwargs):
        """Cargar la fase de extracción."""
        super().setup(request, *args, **kwargs)
        
        project_id = self.kwargs.get('project_id')
        self.phase = get_object_or_404(
            ExtractionPhase.objects.select_related('project'),
            project_id=project_id
        )
    
    def get_queryset(self):
        """
        Filtrar tags según parámetros y permisos del usuario.
        
        Referencia:
        https://docs.djangoproject.com/en/stable/ref/class-based-views/mixins-multiple-object/#django.views.generic.list.MultipleObjectMixin.get_queryset
        """
        queryset = (
            Tag.objects
            .for_phase(self.phase.id)
            .visible_for(self.request.user)
            .select_related('created_by', 'rq_related')
        )
        
        # Aplicar filtros desde query params
        self.filter_form = TagFilterForm(self.request.GET)
        
        if self.filter_form.is_valid():
            # Filtrar por tipo
            tag_type = self.filter_form.cleaned_data.get('type')
            if tag_type:
                queryset = queryset.filter(type=tag_type)
            
            # Filtrar por estado
            status = self.filter_form.cleaned_data.get('status')
            if status:
                queryset = queryset.filter(status=status)
            
            # Buscar por nombre
            search = self.filter_form.cleaned_data.get('search')
            if search:
                queryset = queryset.filter(name__icontains=search)
        
        return queryset.order_by('type', '-created_at')
    
    def get_context_data(self, **kwargs):
        """Agregar contexto adicional."""
        context = super().get_context_data(**kwargs)
        context['phase'] = self.phase
        context['project'] = self.phase.project
        context['filter_form'] = self.filter_form
        
        # Contar tags por estado para badges
        all_tags = Tag.objects.for_phase(self.phase.id)
        context['stats'] = {
            'total': all_tags.count(),
            'deductive': all_tags.deductives().count(),
            'inductive': all_tags.inductives().count(),
            'pending': all_tags.pending_approval().count(),
        }
        
        return context


class PendingTagsListView(LoginRequiredMixin, ProjectMemberRequiredMixin, OwnerRequiredMixin, ListView):
    """
    Listar tags inductivos pendientes de aprobación.
    
    Solo accesible por el líder/owner del proyecto.
    
    Referencia:
    https://docs.djangoproject.com/en/stable/ref/class-based-views/generic-display/#listview
    """
    
    model = Tag
    template_name = 'extraction/templates/partials/dashboard_tabs/pending_tags_list.html'
    context_object_name = 'pending_tags'
    
    def setup(self, request, *args, **kwargs):
        """Cargar la fase de extracción."""
        super().setup(request, *args, **kwargs)
        
        project_id = self.kwargs.get('project_id')
        self.phase = get_object_or_404(
            ExtractionPhase.objects.select_related('project'),
            project_id=project_id
        )
    
    def get_queryset(self):
        """Obtener solo tags inductivos pendientes."""
        service = TagApprovalService()
        return service.get_pending_tags_for_phase(self.phase.id)
    
    def get_context_data(self, **kwargs):
        """Agregar contexto adicional."""
        context = super().get_context_data(**kwargs)
        context['phase'] = self.phase
        context['project'] = self.phase.project
        context['approval_form'] = TagApprovalForm()
        return context


# =============================================================================
# VISTAS DE APROBACIÓN/RECHAZO
# =============================================================================

class TagApproveView(LoginRequiredMixin, ProjectMemberRequiredMixin, OwnerRequiredMixin, View):
    """
    Aprobar un tag inductivo.
    
    Solo accesible por el líder/owner del proyecto.
    Cambia el estado a APPROVED y visibilidad a PUBLIC.
    
    Referencia:
    https://docs.djangoproject.com/en/stable/ref/class-based-views/base/#view
    """
    
    http_method_names = ['post']
    
    def post(self, request, project_id, pk):
        """
        Procesar aprobación del tag.
        
        Args:
            project_id: ID del proyecto
            pk: ID del tag a aprobar
        """
        phase = get_object_or_404(ExtractionPhase, project_id=project_id)
        
        service = TagApprovalService()
        
        try:
            tag = service.approve_tag(
                tag_id=pk,
                approved_by=request.user
            )
            
            messages.success(
                request,
                f'Tag "{tag.name}" aprobado exitosamente. '
                f'Ahora está disponible para todos los researchers.'
            )
            
            # Respuesta AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'tag': {
                        'id': tag.id,
                        'name': tag.name,
                        'status': tag.status,
                        'visibility': tag.visibility,
                    },
                    'message': f'Tag "{tag.name}" aprobado.'
                })
            
        except Tag.DoesNotExist:
            messages.error(request, 'El tag no existe.')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Tag no encontrado.'
                }, status=404)
            
        except ValueError as e:
            messages.error(request, str(e))
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=400)
        
        return redirect(
            f"{reverse('extraction:planning:phase_detail', kwargs={'project_id': phase.project_id})}?tab=pending"
        )


class TagRejectView(LoginRequiredMixin, ProjectMemberRequiredMixin, OwnerRequiredMixin, View):
    """
    Rechazar un tag inductivo.
    
    Solo accesible por el líder/owner del proyecto.
    
    Referencia:
    https://docs.djangoproject.com/en/stable/ref/class-based-views/base/#view
    """
    
    http_method_names = ['post']
    
    def post(self, request, project_id, pk):
        """
        Procesar rechazo del tag.
        
        Args:
            project_id: ID del proyecto
            pk: ID del tag a rechazar
        """
        phase = get_object_or_404(ExtractionPhase, project_id=project_id)
        
        # Obtener motivo del rechazo (opcional)
        reason = request.POST.get('rejection_reason', '')
        
        service = TagApprovalService()
        
        try:
            tag = service.reject_tag(
                tag_id=pk,
                rejected_by=request.user,
                reason=reason
            )
            
            messages.success(
                request,
                f'Tag "{tag.name}" rechazado.'
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Tag "{tag.name}" rechazado.'
                })
            
        except Tag.DoesNotExist:
            messages.error(request, 'El tag no existe.')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Tag no encontrado.'
                }, status=404)
            
        except ValueError as e:
            messages.error(request, str(e))
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=400)
        
        return redirect(
            f"{reverse('extraction:planning:phase_detail', kwargs={'project_id': phase.project_id})}?tab=pending"
        )


class BulkTagApproveView(LoginRequiredMixin, ProjectMemberRequiredMixin, OwnerRequiredMixin, View):
    """
    Aprobar múltiples tags inductivos de una vez.
    
    Útil para aprobar varios tags desde la lista de pendientes.
    
    Referencia:
    https://docs.djangoproject.com/en/stable/ref/class-based-views/base/#view
    """
    
    http_method_names = ['post']
    
    def post(self, request, phase_id):
        """
        Aprobar múltiples tags.
        
        Espera un parámetro 'tag_ids' con IDs separados por coma
        o múltiples parámetros 'tag_ids[]'.
        """
        phase = get_object_or_404(ExtractionPhase, pk=phase_id)
        
        # Obtener IDs de tags (soporta ambos formatos)
        tag_ids = request.POST.getlist('tag_ids[]') or request.POST.get('tag_ids', '').split(',')
        tag_ids = [int(id.strip()) for id in tag_ids if id.strip().isdigit()]
        
        if not tag_ids:
            messages.warning(request, 'No se seleccionaron tags para aprobar.')
            return redirect(
                reverse('extraction:planning:taxonomy:pending_tags', kwargs={
                    'project_id': phase.project_id
                })
            )
        
        service = TagApprovalService()
        approved_tags = service.bulk_approve_tags(tag_ids, request.user)
        
        if approved_tags:
            names = ', '.join([t.name for t in approved_tags])
            messages.success(
                request,
                f'{len(approved_tags)} tag(s) aprobado(s): {names}'
            )
        else:
            messages.warning(
                request,
                'No se pudo aprobar ningún tag. Verifica que estén pendientes.'
            )
        
        return redirect(
            f"{reverse('extraction:planning:phase_detail', kwargs={'project_id': phase.project_id})}?tab=pending"
        )


# =============================================================================
# VISTAS AUXILIARES
# =============================================================================

class UsableTagsAPIView(LoginRequiredMixin, ProjectMemberRequiredMixin, View):
    """
    API para obtener tags disponibles para un usuario.
    
    Usada por JavaScript para cargar tags en el selector de Quote.
    Devuelve JSON con tags agrupados por tipo.
    
    Referencia:
    https://docs.djangoproject.com/en/stable/topics/class-based-views/intro/#handling-forms-with-class-based-views
    """
    
    http_method_names = ['get']
    
    def get(self, request, phase_id):
        """
        Obtener tags usables en formato JSON.
        
        Returns:
            JSON con estructura:
            {
                'tags': {
                    'deductive': [...],
                    'inductive_approved': [...],
                    'inductive_pending': [...],
                }
            }
        """
        phase = get_object_or_404(ExtractionPhase, pk=phase_id)
        
        service = TagUsageService()
        grouped_tags = service.get_tags_grouped_by_type(phase_id, request.user)
        
        def serialize_tag(tag):
            return {
                'id': tag.id,
                'name': tag.name,
                'color': tag.color,
                'type': tag.type,
                'status': tag.status,
                'is_mandatory': tag.is_mandatory,
                'rq_related_id': tag.rq_related_id,
                'created_by_id': tag.created_by_id,
            }
        
        return JsonResponse({
            'tags': {
                'deductive': [serialize_tag(t) for t in grouped_tags['deductive']],
                'inductive_approved': [serialize_tag(t) for t in grouped_tags['inductive_approved']],
                'inductive_pending': [serialize_tag(t) for t in grouped_tags['inductive_pending']],
            }
        })
