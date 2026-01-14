"""
Views - Core Bounded Context
"""
import json
import logging
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.http import FileResponse, JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import DetailView, View

from .forms import QuoteForm
from .models import PaperExtraction, Quote, PaperExtractionStatusChoices
from apps.extraction.core.services import PaperExtractionService
from apps.extraction.shared.exceptions import BusinessRuleViolation

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


class PaperDetailView(LoginRequiredMixin, PaperAccessMixin, DetailView):
    """
    Vista del workspace de extracción de un paper.
    """
    
    model = PaperExtraction
    template_name = 'extraction/templates/paper_detail.html'
    context_object_name = 'paper'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paper = self.object
        phase = paper.extraction_phase
        
        # Tags disponibles
        context['available_tags'] = phase.tags.filter(
            status='APPROVED'
        ).order_by('name')
        
        # Tags obligatorios
        context['mandatory_tags'] = phase.tags.filter(
            status='APPROVED',
            is_mandatory=True
        )
        
        # Quotes ordenadas
        quotes = paper.quotes.select_related('created_by').prefetch_related('tags').all()
        context['quotes'] = sorted(quotes, key=lambda q: q.location.get('page', 0))
        
        # Serializar para JavaScript
        context['quotes_json'] = json.dumps(
            [
                {
                    'id': q.id,
                    'text_fragment': q.text_fragment,
                    'location': q.location,
                    'tags': [
                        {'id': t.id, 'name': t.name, 'color': t.color} 
                        for t in q.tags.all()
                    ]
                }
                for q in context['quotes']
            ],
            cls=DjangoJSONEncoder
        )
        
        # URLs para JavaScript
        project_id = paper.extraction_phase.project_id
        context['pdf_url'] = reverse('extraction:core:paper_pdf', kwargs={'project_id': project_id, 'pk': paper.pk})
        context['quote_create_url'] = reverse('extraction:core:quote_create', kwargs={'project_id': project_id})
        context['quote_delete_url_template'] = reverse(
            'extraction:core:quote_delete', 
            kwargs={'project_id': project_id, 'pk': 0}
        ).replace('/0/', '/{id}/')
        
        logger.info(
            f"Paper workspace loaded: paper_id={paper.id}, "
            f"user={self.request.user.username}, quotes_count={len(context['quotes'])}"
        )
        context['paper_complete_url'] = reverse('extraction:core:paper_complete', kwargs={'project_id': project_id, 'pk': paper.pk})

        
        return context


class PaperPDFView(LoginRequiredMixin, PaperAccessMixin, View):
    """
    Sirve archivos PDF de forma segura.
    """
    
    def get(self, request, project_id, pk):
        """Servir PDF."""
        paper = get_object_or_404(PaperExtraction, pk=pk)
        
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

class PaperCompleteView(LoginRequiredMixin, PaperAccessMixin, View):
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
        paper = get_object_or_404(PaperExtraction, pk=pk)
        
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
            
            return JsonResponse({
                'success': True,
                'message': '✅ Paper completado exitosamente',
                'paper': {
                    'id': paper.id,
                    'status': paper.get_status_display(),
                    'quotes_count': summary['quotes_count'],
                    'coverage_percentage': summary['coverage_percentage']
                }
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

class QuoteCreateView(LoginRequiredMixin, View):
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
            form = QuoteForm(form_data, paper=paper)
            
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
            
            logger.info(f"Quote created successfully: {quote.id}")
            logger.info("="*60)
            
            return JsonResponse({
                'success': True,
                'quote': {
                    'id': quote.id,
                    'text_fragment': quote.text_fragment,
                    'location': quote.location,
                    'tags': [
                        {'id': t.id, 'name': t.name, 'color': t.color}
                        for t in quote.tags.all()
                    ],
                    'created_at': quote.created_at.isoformat()
                }
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
        project = paper.extraction_phase.project
        return (
            user == project.owner or
            paper.assigned_to == user or
            user.is_staff or
            user.is_superuser
        )


class QuoteDeleteView(LoginRequiredMixin, View):
    """API endpoint para eliminar quotes."""
    
    def delete(self, request, project_id, pk):
        quote = get_object_or_404(Quote, pk=pk)
        
        if not self._can_delete_quote(request.user, quote):
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
        project = quote.paper_extraction.extraction_phase.project
        return (
            user == quote.created_by or
            user == project.owner or
            user.is_staff or
            user.is_superuser
        )