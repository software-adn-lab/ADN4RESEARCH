"""
Views - Core Bounded Context
"""
import csv
import json
import logging
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.http import FileResponse, JsonResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView, View

from .forms import QuoteForm
from .dtos import QuoteDTO, PaperCompletionSummaryDTO
from .models import PaperExtraction, Quote, PaperExtractionStatusChoices
from apps.extraction.core.services import PaperExtractionService
from apps.extraction.shared.mixins import ProjectMemberRequiredMixin
from apps.extraction.shared.exceptions import BusinessRuleViolation
from apps.extraction.adapters.acquisition import get_acquisition_adapter

logger = logging.getLogger(__name__)


class PaperAccessMixin(UserPassesTestMixin):
    """
    Mixin para validar acceso a papers.
    
    Compatible tanto con DetailView (que tiene get_object())
    como con View simple (que recibe pk en get()).
    """
    
    def test_func(self):
        """
        Reglas de acceso:
        - Owner del proyecto
        - Researcher asignado
        - Staff/Superuser
        """
        # ✅ Intentar obtener paper de diferentes formas
        paper = self._get_paper()
        
        if not paper:
            return False
        
        user = self.request.user
        project = paper.extraction_phase.project
        
        return (
            user == project.owner or
            paper.assigned_to == user or
            user.is_staff or
            user.is_superuser
        )
    
    def _get_paper(self):
        """
        Obtener paper dependiendo del tipo de vista.
        """
        # Si es DetailView, usar get_object()
        if hasattr(self, 'get_object'):
            return self.get_object()
        
        # Si es View simple, obtener pk de kwargs
        pk = self.kwargs.get('pk')
        if pk:
            return get_object_or_404(PaperExtraction, pk=pk)
        
        # No se pudo obtener el paper
        return None


class PaperDetailView(LoginRequiredMixin, ProjectMemberRequiredMixin, PaperAccessMixin, DetailView):
    """
    Vista del workspace de extracción de un paper.
    """
    
    model = PaperExtraction
    template_name = 'extraction/templates/paper_detail.html'
    context_object_name = 'paper'

    def get_queryset(self):
        project_id = self.kwargs.get('project_id')
        return PaperExtraction.objects.filter(
            extraction_phase__project_id=project_id
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paper = self.object
        phase = paper.extraction_phase
        
        # Tags disponibles
        context['available_tags'] = phase.tags.usable_by(
            self.request.user
        ).order_by('name')
        
        # Tags obligatorios
        context['mandatory_tags'] = phase.tags.mandatory()
        
        # Quotes ordenadas
        quotes = paper.quotes.select_related('created_by').prefetch_related('tags').all()
        sorted_quotes = sorted(quotes, key=lambda q: q.location.get('page', 0))
        context['quotes'] = sorted_quotes

        # Serializar para JavaScript
        quote_dtos = [QuoteDTO.from_model(q) for q in sorted_quotes]
        context['quotes_json'] = json.dumps(
            [dto.to_dict() for dto in quote_dtos],
            cls=DjangoJSONEncoder
        )
        
        # URLs para JavaScript
        project_id = paper.extraction_phase.project_id
        
        # ✅ Get PDF URL from Acquisition adapter (S3/filesystem compatible)
        pdf_url = self._get_pdf_url(paper)
        context['pdf_url'] = pdf_url
        context['has_pdf'] = pdf_url is not None
        
        context['quote_create_url'] = reverse('extraction:core:quote_create', kwargs={'project_id': project_id})
        context['quote_delete_url_template'] = reverse(
            'extraction:core:quote_delete', 
            kwargs={'project_id': project_id, 'pk': 0}
        ).replace('/0/', '/{id}/')
        context['paper_status'] = paper.status
        
        logger.info(
            f"Paper workspace loaded: paper_id={paper.id}, "
            f"user={self.request.user.username}, quotes_count={len(context['quotes'])}, "
            f"has_pdf={context['has_pdf']}"
        )
        context['paper_complete_url'] = reverse('extraction:core:paper_complete', kwargs={'project_id': project_id, 'pk': paper.pk})
        context['paper_reopen_url'] = reverse('extraction:core:paper_reopen', kwargs={'project_id': project_id, 'pk': paper.pk})

        return context
    
    def _get_pdf_url(self, paper):
        """
        Get PDF URL from Acquisition module through adapter.
        
        Uses the AcquisitionAdapter to access pdf_url in a centralized way,
        supporting both filesystem and S3/MinIO storage backends.
        
        Returns:
            PDF URL string or None if PDF not available
        """
        try:
            from apps.extraction.adapters.acquisition import get_acquisition_adapter
            
            adapter = get_acquisition_adapter()
            pdf_url = adapter.get_study_pdf_url(
                study_id=str(paper.study_id),
                project_id=paper.extraction_phase.project_id
            )
            
            if pdf_url:
                logger.debug(
                    f"[PAPER DETAIL] Got PDF URL for paper {paper.id}: {pdf_url}"
                )
            else:
                logger.debug(
                    f"[PAPER DETAIL] No PDF available for paper {paper.id}"
                )
            
            return pdf_url
            
        except Exception as e:
            logger.error(
                f"[PAPER DETAIL] Failed to get PDF URL for paper {paper.id}: {e}",
                exc_info=True
            )
            return None


class PaperPDFView(LoginRequiredMixin, ProjectMemberRequiredMixin, PaperAccessMixin, View):
    """
    Sirve archivos PDF de forma segura.
    """
    
    def get(self, request, project_id, pk):
        """Servir PDF."""
        paper = get_object_or_404(
            PaperExtraction,
            pk=pk,
            extraction_phase__project_id=project_id
        )
        
        # Logging
        logger.info(
            f"PDF request: paper_id={pk}, user={request.user.username}, "
            f"path={paper.path}"
        )
        
        # Validar permisos (ya validado por mixin, pero explícito para claridad)
        if not self.test_func():
            logger.warning(f"Permission denied: user={request.user.username}, paper={pk}")
            raise PermissionDenied("No tienes permiso para ver este documento")
        
        # Obtener ruta segura
        file_path = self._get_safe_path(paper.path)
        
        if not file_path.exists():
            logger.error(f"PDF not found: {file_path}")
            raise Http404("El archivo PDF no existe")
        
        try:
            # Servir archivo
            response = FileResponse(
                file_path.open('rb'),
                content_type='application/pdf'
            )
            
            # Headers
            safe_filename = self._sanitize_filename(paper.study.title)
            response['Content-Disposition'] = f'inline; filename="{safe_filename}.pdf"'
            response['X-Content-Type-Options'] = 'nosniff'
            
            logger.info(
                f"PDF served: paper_id={pk}, size={file_path.stat().st_size} bytes"
            )
            
            return response
            
        except Exception as e:
            logger.exception(f"Error serving PDF: {e}")
            raise Http404("Error al servir el archivo PDF")
    
    def _get_safe_path(self, relative_path):
        """
        Validar ruta contra Path Traversal.
        """
        media_root = Path(settings.MEDIA_ROOT).resolve()
        absolute_path = (media_root / relative_path).resolve()
        
        try:
            absolute_path.relative_to(media_root)
        except ValueError:
            logger.error(
                f"Path traversal attempt: {relative_path} -> {absolute_path}"
            )
            raise PermissionDenied("Ruta de archivo inválida")
        
        return absolute_path
    
    def _sanitize_filename(self, filename):
        """Sanitizar nombre de archivo."""
        return (
            filename
            .replace('"', '')
            .replace("'", '')
            .replace('/', '-')
            .replace('\\', '-')
        )[:100]

class PaperCompleteView(LoginRequiredMixin, ProjectMemberRequiredMixin, PaperAccessMixin, View):
    """
    Endpoint para marcar un paper como completado.
    
    Business Rules (delegadas al Service):
    - Solo owner o researcher asignado pueden completar
    - Debe tener al menos una quote
    - Todas las tags obligatorias deben estar cubiertas
    
    Architecture:
    - Vista: Validación de permisos y HTTP handling
    - Service: Lógica de negocio y orquestación
    - Model: Queries y persistencia
    
    Referencia Django CBV:
    https://docs.djangoproject.com/en/stable/ref/class-based-views/base/#view
    """
    
    def post(self, request, project_id, pk):
        """
        Procesar solicitud de completar paper.
        
        Args:
            request: HTTP request
            pk: ID del paper
            
        Returns:
            JsonResponse con resultado
        """
        paper = get_object_or_404(
            PaperExtraction,
            pk=pk,
            extraction_phase__project_id=project_id
        )
        
        # Validar permisos (responsabilidad de la vista)
        if not self._can_complete_paper(request.user, paper):
            logger.warning(
                f"Permission denied: user={request.user.username}, "
                f"paper_id={paper.id}, action=complete"
            )
            return JsonResponse(
                {'error': 'No tienes permiso para completar este paper'},
                status=403
            )
        
        # Delegar lógica de negocio al servicio
        service = PaperExtractionService()
        
        try:
            # Service maneja validaciones y transiciones
            paper = service.attempt_complete_paper(paper, request.user)
            
            # Obtener resumen para la respuesta
            summary = service.get_completion_summary(paper)
            
            paper_dto = PaperCompletionSummaryDTO(
                id=paper.id,
                status=paper.get_status_display(),
                quotes_count=summary['quotes_count'],
                coverage_percentage=summary['coverage_percentage']
            )

            return JsonResponse({
                'success': True,
                'message': '✅ Paper completado exitosamente',
                'paper': paper_dto.to_dict()
            })
            
        except BusinessRuleViolation as e:
            # Service lanzó excepción de negocio
            logger.info(
                f"Paper completion rejected: paper_id={paper.id}, "
                f"reason={str(e)}"
            )
            return JsonResponse(
                {'error': str(e)},
                status=400
            )
            
        except Exception as e:
            # Error inesperado
            logger.exception(
                f"Unexpected error completing paper: paper_id={paper.id}"
            )
            return JsonResponse(
                {'error': 'Error interno del servidor'},
                status=500
            )
    
    def _can_complete_paper(self, user, paper):
        """
        Validar permisos para completar.
        
        Nota: Esta es validación de permisos (infraestructura),
        no lógica de negocio. Por eso está en la vista.
        
        Args:
            user: Usuario solicitante
            paper: Paper a completar
            
        Returns:
            bool: Si tiene permisos
        """
        project = paper.extraction_phase.project
        return (
            user == project.owner or
            paper.assigned_to == user or
            user.is_staff or
            user.is_superuser
        )

class PaperReopenView(LoginRequiredMixin, ProjectMemberRequiredMixin, PaperAccessMixin, View):
    """
    Endpoint para reabrir un paper completado.
    """

    def post(self, request, project_id, pk):
        """
        Procesar solicitud de reabrir paper.
        """
        paper = get_object_or_404(
            PaperExtraction,
            pk=pk,
            extraction_phase__project_id=project_id
        )

        if not self._can_reopen_paper(request.user, paper):
            logger.warning(
                f"Permission denied: user={request.user.username}, "
                f"paper_id={paper.id}, action=reopen"
            )
            return JsonResponse(
                {'error': 'No tienes permiso para reabrir este paper'},
                status=403
            )

        if paper.status == PaperExtractionStatusChoices.COMPLETED:
            paper.status = PaperExtractionStatusChoices.IN_PROGRESS
            paper.save(update_fields=['status', 'updated_at'])
            logger.info(f"Paper reabierto: id={paper.id}, user={request.user.username}")
            return JsonResponse({
                'success': True,
                'message': 'Extracción reabierta. Ahora puedes editarla de nuevo.'
            })
        
        return JsonResponse(
            {'error': 'El paper no está completado.'},
            status=400
        )

    def _can_reopen_paper(self, user, paper):
        """
        Validar permisos para reabrir. Por ahora, los mismos que para completar.
        """
        project = paper.extraction_phase.project
        return (
            user == project.owner or
            paper.assigned_to == user or
            user.is_staff or
            user.is_superuser
        )


class QuoteCreateView(LoginRequiredMixin, ProjectMemberRequiredMixin, View):
    """API endpoint para crear quotes (JSON)."""
    
    def post(self, request, project_id):
        try:
            # Parsear datos
            data = json.loads(request.body)
            
            # ✅ Debug logging
            logger.info("="*60)
            logger.info("QUOTE CREATE REQUEST")
            logger.info("="*60)
            logger.info(f"Request data: {data}")
            logger.info(f"User: {request.user.username}")
            
            # Obtener paper
            paper_id = data.get('paper_extraction_id')
            logger.info(f"Paper ID from request: {paper_id}")
            
            if not paper_id:
                logger.error("Missing paper_extraction_id")
                return JsonResponse(
                    {'error': 'paper_extraction_id es requerido'},
                    status=400
                )
            
            paper = get_object_or_404(PaperExtraction, pk=paper_id)
            logger.info(f"Paper found: {paper.id}")
            
            # Validar permisos
            if not self._can_create_quote(request.user, paper):
                if paper.status == PaperExtractionStatusChoices.COMPLETED:
                    logger.error("Paper is completed, cannot create quotes")
                    return JsonResponse(
                        {'error': 'No se pueden agregar quotes a un paper completado'},
                        status=403
                    )
                logger.error("Permission denied")
                return JsonResponse(
                    {'error': 'No tienes permiso para crear quotes en este paper'},
                    status=403
                )
            
            # ✅ Preparar datos para el formulario
            form_data = {
                'text_fragment': data.get('text_fragment', ''),
                'paper_extraction': paper.id,
                'tags': data.get('tags', []),
            }
            
            logger.info(f"Form data: {form_data}")
            
            # Crear formulario
            form = QuoteForm(form_data, paper=paper, user=request.user)
            
            # Validar
            if not form.is_valid():
                logger.error(f"Form validation failed: {form.errors}")
                return JsonResponse(
                    {
                        'error': 'Datos inválidos', 
                        'errors': form.errors.get_json_data()
                    },
                    status=400
                )
            
            # Guardar
            quote = form.save(commit=False)
            quote.created_by = request.user
            quote.location = data.get('location', {})
            quote.save()
            form.save_m2m()
            
            # ✅ Actualizar estado del paper a IN_PROGRESS si está en PENDING
            if paper.status == PaperExtractionStatusChoices.PENDING:
                paper.status = PaperExtractionStatusChoices.IN_PROGRESS
                paper.save(update_fields=['status', 'updated_at'])
                logger.info(
                    f"Paper status updated: paper_id={paper.id}, "
                    f"new_status={paper.status}, triggered_by=quote_creation"
                )
            
            logger.info(f"Quote created successfully: {quote.id}")
            logger.info("="*60)
            
            quote_dto = QuoteDTO.from_model(quote, include_created_at=True)
            return JsonResponse({
                'success': True,
                'quote': quote_dto.to_dict()
            }, status=201)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return JsonResponse(
                {'error': 'JSON inválido', 'detail': str(e)},
                status=400
            )
        except Exception as e:
            logger.exception("Unexpected error creating quote")
            return JsonResponse(
                {'error': 'Error interno del servidor', 'detail': str(e)},
                status=500
            )
    
    def _can_create_quote(self, user, paper):
        """Validar permisos de creación."""
        # No permitir crear quotes en papers completados
        if paper.status == PaperExtractionStatusChoices.COMPLETED:
            return False
        
        project = paper.extraction_phase.project
        return (
            user == project.owner or
            paper.assigned_to == user or
            user.is_staff or
            user.is_superuser
        )


class QuoteDeleteView(LoginRequiredMixin, ProjectMemberRequiredMixin, View):
    """API endpoint para eliminar quotes."""
    
    def post(self, request, project_id, pk):
        """Handle POST requests for quote deletion (from AJAX)."""
        return self._delete_quote(request, pk)
    
    def delete(self, request, project_id, pk):
        """Handle DELETE requests for quote deletion (RESTful)."""
        return self._delete_quote(request, pk)
    
    def _delete_quote(self, request, pk):
        quote = get_object_or_404(Quote, pk=pk)
        
        if not self._can_delete_quote(request.user, quote):
            if quote.paper_extraction.status == PaperExtractionStatusChoices.COMPLETED:
                return JsonResponse(
                    {'error': 'No se pueden eliminar quotes de un paper completado'},
                    status=403
                )
            return JsonResponse(
                {'error': 'No tienes permiso para eliminar esta quote'},
                status=403
            )
        
        try:
            quote_id = quote.id
            quote.delete()
            
            logger.info(f"Quote deleted: id={quote_id}, user={request.user.username}")
            
            return JsonResponse({
                'success': True,
                'message': 'Quote eliminada exitosamente',
                'quote_id': quote_id
            })
            
        except Exception as e:
            logger.exception("Error deleting quote")
            return JsonResponse({'error': 'Error al eliminar la quote'}, status=500)
    
    def _can_delete_quote(self, user, quote):
        """Validar permisos de eliminación."""
        # No permitir eliminar quotes de papers completados
        if quote.paper_extraction.status == PaperExtractionStatusChoices.COMPLETED:
            return False
        
        project = quote.paper_extraction.extraction_phase.project
        return (
            user == quote.created_by or
            user == project.owner or
            user.is_staff or
            user.is_superuser
        )


class PaperReassignView(LoginRequiredMixin, ProjectMemberRequiredMixin, View):
    """
    Vista para reasignar un paper a otro miembro del proyecto.
    
    Solo el owner del proyecto puede reasignar papers.
    """
    
    def post(self, request, project_id, pk):
        """
        POST /project/<project_id>/extraction/papers/<pk>/reassign/
        
        JSON payload:
        {
            "assigned_to_id": <user_id>
        }
        """
        try:
            # Obtener paper
            paper = get_object_or_404(PaperExtraction, pk=pk)
            phase = paper.extraction_phase
            project = phase.project
            
            # Validar que el usuario sea owner
            if request.user != project.owner and not request.user.is_staff:
                return JsonResponse(
                    {'error': 'Solo el owner puede reasignar papers'},
                    status=403
                )
            
            # Obtener datos
            data = json.loads(request.body)
            assigned_to_id = data.get('assigned_to_id')
            
            if not assigned_to_id:
                return JsonResponse(
                    {'error': 'assigned_to_id es requerido'},
                    status=400
                )
            
            # Obtener usuario a asignar
            from django.contrib.auth import get_user_model
            User = get_user_model()
            assigned_user = get_object_or_404(User, pk=assigned_to_id)
            
            # Validar que sea miembro del proyecto
            from apps.project.structure.models.project_models import Membership
            is_member = (
                assigned_user == project.owner or
                Membership.objects.filter(
                    project=project,
                    user=assigned_user
                ).exists()
            )
            
            if not is_member:
                return JsonResponse(
                    {'error': f'{assigned_user.username} no es miembro del proyecto'},
                    status=400
                )
            
            # Reasignar
            old_assigned_to = paper.assigned_to
            paper.assigned_to = assigned_user
            paper.save(update_fields=['assigned_to', 'updated_at'])
            
            logger.info(
                f"Paper {pk} reasignado de {old_assigned_to.username if old_assigned_to else 'nadie'} "
                f"a {assigned_user.username} por {request.user.username}"
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Paper reasignado a {assigned_user.username}',
                'assigned_to': {
                    'id': assigned_user.id,
                    'username': assigned_user.username
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse(
                {'error': 'JSON inválido'},
                status=400
            )
        except Exception as e:
            logger.exception("Error reasignando paper")
            return JsonResponse(
                {'error': f'Error al reasignar: {str(e)}'},
                status=500
            )

class PaperUpdatePDFView(LoginRequiredMixin, ProjectMemberRequiredMixin, PaperAccessMixin, View):
    """
    View to handle updating the PDF of a PaperExtraction.
    """
    def post(self, request, project_id, pk):
        paper = get_object_or_404(PaperExtraction, pk=pk, extraction_phase__project_id=project_id)

        if 'pdf_file' not in request.FILES:
            messages.error(request, 'No PDF file was provided.')
            return redirect(request.META.get('HTTP_REFERER', '/'))

        file = request.FILES['pdf_file']

        # Permission check (only owner or staff can do this)
        project = paper.extraction_phase.project
        if not (request.user == project.owner or request.user.is_staff):
            messages.error(request, 'You do not have permission to update the PDF for this paper.')
            return redirect(request.META.get('HTTP_REFERER', '/'))

        try:
            # Delete all existing quotes for this paper
            deleted_count, _ = paper.quotes.all().delete()
            logger.info(f"Deleted {deleted_count} quotes from PaperExtraction {paper.id} before PDF update.")

            adapter = get_acquisition_adapter()
            upload_result = adapter.upload_study_pdf(
                study_id=str(paper.study_id),
                file_obj=file,
                filename=file.name,
                user=request.user
            )

            # Update PaperExtraction instance
            paper.path = upload_result.get('pdf_path')
            # The study_id should not change when updating a PDF for an existing study,
            # but we can log if something unexpected happens.
            if str(paper.study_id) != upload_result.get('study_id'):
                logger.warning(f"Study ID mismatch for PaperExtraction {paper.id} during PDF update.")

            paper.save(update_fields=['path', 'updated_at'])

            messages.success(request, f'Successfully updated PDF for "{paper.study.title}".')
            logger.info(f"PDF for PaperExtraction {paper.id} updated by {request.user.username}")

        except Exception as e:
            logger.error(f"Failed to update PDF for PaperExtraction {paper.id}: {e}", exc_info=True)
            messages.error(request, f'An error occurred while updating the PDF: {e}')

        return redirect(f"{reverse('extraction:planning:phase_detail', kwargs={'project_id': project_id})}?tab=studies")


class ExportQuotesCSVView(LoginRequiredMixin, ProjectMemberRequiredMixin, View):
    """
    Exporta todas las quotes a CSV con atributos completos.
    
    Incluye:
    - Atributos de la quote (id, text_fragment, location, created_at, updated_at)
    - Usuario que realizó la extracción (created_by.username)
    - UUID y título del estudio
    - Path del paper_extraction
    - Tags asociados a la quote
    """
    
    def get(self, request, project_id):
        """Exporta las quotes de la fase de extracción a CSV."""
        try:
            # Obtener la fase de extracción del proyecto
            from apps.extraction.planning.models import ExtractionPhase
            phase = get_object_or_404(ExtractionPhase, project_id=project_id)
            
            # Obtener todas las quotes de la fase
            quotes = Quote.objects.filter(
                paper_extraction__extraction_phase=phase
            ).select_related(
                'paper_extraction',
                'paper_extraction__study',
                'created_by'
            ).prefetch_related('tags')
            
            # Crear archivo CSV en memoria
            output = StringIO()
            writer = csv.writer(output, quoting=csv.QUOTE_ALL)
            
            # Escribir encabezados
            headers = [
                'Quote ID',
                'Text Fragment',
                'Location',
                'Extracted By',
                'Study UUID',
                'Study Title',
                'Paper Path',
                'Tags',
                'Created At',
                'Updated At'
            ]
            writer.writerow(headers)
            
            # Escribir datos de cada quote
            for quote in quotes:
                tags_str = ', '.join([tag.name for tag in quote.tags.all()]) or ''
                location_str = json.dumps(quote.location, ensure_ascii=False) if quote.location else ''
                
                row = [
                    quote.id,
                    quote.text_fragment or '',
                    location_str,
                    quote.created_by.username if quote.created_by else '',
                    str(quote.paper_extraction.study.uuid) if quote.paper_extraction and quote.paper_extraction.study else '',
                    quote.paper_extraction.study.title if quote.paper_extraction and quote.paper_extraction.study else '',
                    quote.paper_extraction.path or '' if quote.paper_extraction else '',
                    tags_str,
                    quote.created_at.isoformat() if quote.created_at else '',
                    quote.updated_at.isoformat() if quote.updated_at else ''
                ]
                writer.writerow(row)
            
            # Crear respuesta HTTP con el CSV
            csv_content = output.getvalue()
            response = HttpResponse(
                csv_content,
                content_type='text/csv; charset=utf-8'
            )
            response['Content-Disposition'] = 'attachment; filename="quotes_export.csv"'
            
            logger.info(
                f"Usuario {request.user.username} exportó {quotes.count()} quotes del proyecto {project_id}"
            )
            
            return response
            
        except Exception as e:
            logger.exception(f"Error exportando quotes: {str(e)}")
            return JsonResponse(
                {'error': f'Error al exportar: {str(e)}'},
                status=500
            )