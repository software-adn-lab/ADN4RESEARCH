"""
Bounded Context: Core
Responsabilidad: Gestión de papers y quotes (extracción de contenido)
"""
import os
import logging
import json
from pathlib import Path
from django.http import JsonResponse, FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils.decorators import method_decorator

from .models import PaperExtraction,Quote
from ..taxonomy.models import Tag


logger = logging.getLogger(__name__)

class PDFServeView(LoginRequiredMixin, View):
    """
    Sirve archivos PDF para PDF.js.
    
    No necesita @xframe_options_exempt porque PDF.js carga el archivo
    directamente via fetch(), no en un iframe.
    
    Headers críticos para PDF.js:
    - Content-Type: application/pdf
    - Content-Disposition: inline
    - Access-Control-Allow-Origin (si se sirve desde diferente puerto)
    """
    
    def get(self, request, paper_id):
        paper = get_object_or_404(PaperExtraction, pk=paper_id)
        
        # Validación de permisos
        if not self._user_can_access_paper(request.user, paper):
            logger.warning(
                f"Permission denied: user={request.user.username}, paper={paper_id}"
            )
            raise PermissionDenied("No tienes permiso para ver este documento")
        
        # Obtener ruta segura del archivo
        file_path = self._get_safe_path(paper.path)
        
        # Verificar existencia del archivo
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            raise Http404("El archivo PDF no existe")
        
        # Servir archivo con headers optimizados para PDF.js
        try:
            response = FileResponse(
                open(file_path, 'rb'),
                content_type='application/pdf'
            )
            
            # Nombre del archivo para el navegador
            safe_filename = self._sanitize_filename(paper.study.title)
            response['Content-Disposition'] = f'inline; filename="{safe_filename}.pdf"'
            
            # Headers de seguridad
            response['X-Content-Type-Options'] = 'nosniff'
            
            # CORS (solo si es necesario - cuando Django y frontend están en puertos diferentes)
            # Descomenta si tienes problemas de CORS
            # response['Access-Control-Allow-Origin'] = request.META.get('HTTP_ORIGIN', '*')
            # response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            # response['Access-Control-Allow-Headers'] = 'Content-Type'
            
            logger.info(
                f"PDF served successfully for PDF.js: "
                f"paper={paper_id}, user={request.user.id}, "
                f"path={file_path}, size={os.path.getsize(file_path)} bytes"
            )
            
            return response
        
        except Exception as e:
            logger.exception(f"Error serving PDF: {e}")
            raise Http404("Error al servir el archivo PDF")
    
    def _user_can_access_paper(self, user, paper):
        """
        Valida permisos de acceso al paper.
        
        Reglas:
        1. Owner del proyecto
        2. Researcher asignado
        3. Staff/Superuser
        """
        project = paper.extraction_phase.project
        
        return (
            user == project.owner or
            paper.assigned_to == user or
            user.is_staff or
            user.is_superuser
        )
    
    def _get_safe_path(self, relative_path):
        """
        Valida y normaliza la ruta del archivo.
        Protección contra Path Traversal.
        
        Args:
            relative_path: Ruta relativa a MEDIA_ROOT (ej: "test_papers/paper_1.pdf")
            
        Returns:
            str: Ruta absoluta validada
            
        Raises:
            PermissionDenied: Si la ruta está fuera de MEDIA_ROOT
        """
        media_root = Path(settings.MEDIA_ROOT).resolve()
        absolute_path = (media_root / relative_path).resolve()
        
        # Validar que esté dentro de MEDIA_ROOT
        try:
            absolute_path.relative_to(media_root)
        except ValueError:
            logger.error(
                f"Path Traversal attempt detected: {relative_path} "
                f"resolved to {absolute_path}, outside {media_root}"
            )
            raise PermissionDenied("Ruta de archivo inválida")
        
        return str(absolute_path)
    
    def _sanitize_filename(self, filename):
        """
        Sanitiza el nombre del archivo para Content-Disposition.
        
        Args:
            filename: Nombre original del archivo
            
        Returns:
            str: Nombre sanitizado (máx 100 caracteres, sin comillas ni slashes)
        """
        sanitized = (
            filename
            .replace('"', '')
            .replace("'", '')
            .replace('/', '-')
            .replace('\\', '-')
        )
        return sanitized[:100]

class PaperWorkspaceView(LoginRequiredMixin, DetailView):
    """Vista del workspace de extracción de un paper."""
    
    model = PaperExtraction
    template_name = 'paper_extraction_detail.html'
    context_object_name = 'paper'

    def get(self, request, *args, **kwargs):
        """Override para agregar logging."""
        logger.info(f"=== PaperWorkspaceView GET ===")
        logger.info(f"User: {request.user.username} (ID: {request.user.id})")
        logger.info(f"Paper PK: {kwargs.get('pk')}")
        
        response = super().get(request, *args, **kwargs)
        
        logger.info(f"Template usado: {self.template_name}")
        logger.info(f"Status code: {response.status_code}")
        
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 🐛 DEBUG: Agregar logs
        print("\n" + "="*60)
        print("WORKSPACE CONTEXT DEBUG")
        print("="*60)
        print(f"Paper ID: {self.object.id}")
        print(f"Extraction Phase: {self.object.extraction_phase}")
        print(f"Extraction Phase ID: {self.object.extraction_phase.id}")
        
        # Tags disponibles (aprobados)
        available_tags = self.object.extraction_phase.tags.filter(
            status='APPROVED'
        )
        print(f"\nAvailable Tags Query: {available_tags.query}")
        print(f"Available Tags Count: {available_tags.count()}")
        for tag in available_tags:
            print(f"  - {tag.name} (mandatory: {tag.is_mandatory})")
        
        context['available_tags'] = available_tags

        # Tags obligatorios
        mandatory_tags = self.object.extraction_phase.tags.filter(
            status='APPROVED',
            is_mandatory=True
        )
        print(f"\nMandatory Tags Query: {mandatory_tags.query}")
        print(f"Mandatory Tags Count: {mandatory_tags.count()}")
        for tag in mandatory_tags:
            print(f"  - {tag.name}")
        
        context['mandatory_tags'] = mandatory_tags

        # Quotes existentes
        quotes_list = list(
            self.object.quotes.values('id', 'text_fragment', 'location')
        )
        print(f"\nQuotes Count: {len(quotes_list)}")
        
        context['quotes_list'] = quotes_list
        
        print("="*60 + "\n")
        
        return context


class QuoteCreateView(LoginRequiredMixin, View):
    """API para crear quotes desde el PDF viewer."""
    
    def post(self, request):
        try:
            # 1. Parsear JSON del body
            data = json.loads(request.body)
            
            logger.info("="*60)
            logger.info("QUOTE CREATION REQUEST")
            logger.info("="*60)
            logger.info(f"User: {request.user}")
            logger.info(f"Data received: {data}")
            
            # 2. Validar campos requeridos
            text_fragment = data.get('text_fragment')
            paper_id = data.get('paper_extraction_id')
            tag_ids = data.get('tags', [])
            location = data.get('location', {})
            
            if not text_fragment:
                logger.error("Missing text_fragment")
                return JsonResponse({
                    'error': 'text_fragment es requerido'
                }, status=400)
            
            if not paper_id:
                logger.error("Missing paper_extraction_id")
                return JsonResponse({
                    'error': 'paper_extraction_id es requerido'
                }, status=400)
            
            if not tag_ids:
                logger.error("Missing tags")
                return JsonResponse({
                    'error': 'Debe seleccionar al menos una etiqueta'
                }, status=400)
            
            # 3. Obtener paper
            try:
                paper = PaperExtraction.objects.get(pk=paper_id)
                logger.info(f"Paper found: {paper.id}")
            except PaperExtraction.DoesNotExist:
                logger.error(f"Paper not found: {paper_id}")
                return JsonResponse({
                    'error': f'Paper {paper_id} no encontrado'
                }, status=404)
            
            # 4. Validar permisos
            if not self._user_can_create_quote(request.user, paper):
                logger.error(f"Permission denied for user {request.user}")
                return JsonResponse({
                    'error': 'No tienes permiso para crear quotes en este paper'
                }, status=403)
            
            # 5. Crear Quote
            quote = Quote.objects.create(
                paper_extraction=paper,
                text_fragment=text_fragment,
                location=location,  # JSONField
                created_by=request.user
            )
            logger.info(f"Quote created: {quote.id}")
            
            # 6. Asignar tags
            tags = Tag.objects.filter(id__in=tag_ids)
            
            if tags.count() != len(tag_ids):
                logger.warning(f"Some tags not found. Expected {len(tag_ids)}, found {tags.count()}")
            
            quote.tags.set(tags)
            logger.info(f"Tags assigned: {[tag.name for tag in tags]}")
            
            # 7. Response exitoso
            response_data = {
                'success': True,
                'quote': {
                    'id': quote.id,
                    'text_fragment': quote.text_fragment,
                    'location': quote.location,
                    'tags': [
                        {
                            'id': tag.id,
                            'name': tag.name,
                            'color': tag.color
                        }
                        for tag in quote.tags.all()
                    ],
                    'created_at': quote.created_at.isoformat()
                }
            }
            
            logger.info("Quote created successfully")
            logger.info("="*60)
            
            return JsonResponse(response_data, status=201)
        
        except json.JSONDecodeError as e:
            logger.exception("Invalid JSON in request body")
            return JsonResponse({
                'error': 'JSON inválido en el body',
                'detail': str(e)
            }, status=400)
        
        except Exception as e:
            logger.exception("Unexpected error creating quote")
            return JsonResponse({
                'error': 'Error interno del servidor',
                'detail': str(e)
            }, status=500)
    
    def _user_can_create_quote(self, user, paper):
        """Valida si el usuario puede crear quotes en este paper."""
        project = paper.extraction_phase.project
        
        return (
            user == project.owner or
            paper.assigned_to == user or
            user.is_staff or
            user.is_superuser
        )