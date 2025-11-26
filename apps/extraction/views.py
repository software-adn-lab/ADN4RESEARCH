import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .core.services import ExtractionService
from .core.models import PaperExtraction, Quote
from .taxonomy.services import TagService
from .taxonomy.models import Tag
from .planning.services import ExtractionPhaseService
from .planning.models import ExtractionPhase
from .shared.exceptions import BusinessRuleViolation, ResourceNotFound


class DashboardView(View):
    """Vista principal del dashboard de extracción"""
    
    def get(self, request):
        # Simulación de usuario y proyecto (en producción vendría de la sesión)
        user = {
            'id': request.GET.get('user_id', 1),
            'name': request.GET.get('user_name', 'Carlos'),
            'role': request.GET.get('role', 'owner')  # 'owner' o 'researcher'
        }
        project_id = int(request.GET.get('project_id', 1))
        
        # Obtener datos de servicios
        extraction_service = ExtractionService()
        tag_service = TagService()
        phase_service = ExtractionPhaseService()
        
        # Datos de la fase
        phase = phase_service.get_or_create_phase(project_id)
        phase_data = phase_service.get_phase_status(project_id)
        
        # Obtener papers
        if user['role'] == 'owner':
            raw_papers = extraction_service.get_all_papers(project_id)
            papers = self._format_owner_papers(raw_papers, phase, extraction_service)
        else:
            raw_papers = extraction_service.get_researcher_papers(project_id, int(user['id']))
            papers = self._format_researcher_papers(raw_papers)  # Nuevo formateador
        
        # Obtener tags
        if user['role'] == 'owner':
            tags = tag_service.repository.list_by_project(project_id)
        else:
            tags = tag_service.repository.get_tags_for_user(project_id, int(user['id']))
        
        # Obtener quotes
        quotes = self._get_all_quotes(project_id)
        
        # Serializar datos
        papers_json = self._serialize_papers(papers)
        tags_json = self._serialize_tags(tags)
        quotes_json = self._serialize_quotes(quotes)
        
        # Estadísticas
        total_papers = len(papers)
        completed_papers = sum(1 for p in papers if p.get('status') == 'Done')
        
        context = {
            'user': user,
            'project': {
                'id': project_id,
                'name': 'Proyecto SLR: Modernización de Sistemas',
                'description': 'Revisión sistemática sobre patrones de modernización.'
            },
            'phase': {
                'status': phase.status if phase else 'configuration',
                'end_date': phase.end_date.isoformat() if phase and phase.end_date else None,
                'auto_close': phase.auto_close if phase else False,
            },
            'papers_json': json.dumps(papers_json),
            'tags_json': json.dumps(tags_json),
            'quotes_json': json.dumps(quotes_json),
            'total_papers': total_papers,
            'completed_papers': completed_papers,
        }
        
        return render(request, 'dashboard.html', context)

    def _format_owner_papers(self, raw_papers, phase, extraction_service):
        """
        Formatea los datos brutos del servicio get_all_papers, añadiendo la información
        de asignación (para saber quién está a cargo).
        """
        from .planning.repositories import PaperAssignmentRepository
        assignment_repo = PaperAssignmentRepository()

        papers = []

        for p in raw_papers:
            researcher_id = None
            researcher_name = None

            # Lógica de asignación (solo si la fase está activa)
            if phase:
                # Reutilizar lógica para buscar la asignación
                assignment = assignment_repo.get_by_study_and_phase(p['study_id'], phase.id)
                if assignment:
                    researcher_id = assignment.researcher_id
                    researcher_name = f"Researcher #{researcher_id}"

            papers.append({
                'id': p['study_id'],  # Mapeo de study_id a id (Frontend espera 'id')
                'extraction_id': p['extraction_id'],
                'title': p['title'],
                'authors': p['authors'],
                'status': p['status'],
                'researcher_id': researcher_id,
                'researcher_name': researcher_name,
                'progress': p['progress'],
                'pdf_url': p['pdf_url'],
            })

        return papers


    def _format_researcher_papers(self, raw_papers):
        """
        Mapea el output del servicio del researcher al formato que espera el frontend.
        """
        papers = []

        for p in raw_papers:
            papers.append({
                'id': p['study_id'],  # Mapeo de study_id a id
                'extraction_id': p['extraction_id'],
                'title': p['title'],
                'authors': p['authors'],
                'status': p['status'],
                'researcher_id': p['researcher_id'],
                'researcher_name': p['researcher_name'],
                'progress': p['progress'],
                'pdf_url': p['pdf_url'],
                # Agrega otros campos si los necesitas en el frontend
            })

        return papers

    def _get_all_papers_for_owner(self, project_id, phase, extraction_service):
        """Obtiene todos los papers con info de asignación para el Owner"""
        from .planning.repositories import PaperAssignmentRepository
        
        papers = []
        extractions = PaperExtraction.objects.filter(project_id=project_id)
        assignment_repo = PaperAssignmentRepository()
        
        for ext in extractions:
            # Obtener researcher asignado
            researcher_id = None
            researcher_name = None
            if phase:
                assignment = assignment_repo.get_by_study_and_phase(ext.study_id, phase.id)
                if assignment:
                    researcher_id = assignment.researcher_id
                    researcher_name = f"Researcher #{researcher_id}"  # En producción: obtener nombre real
            
            progress = extraction_service.get_extraction_progress(ext.id)
            
            papers.append({
                'id': ext.study_id,
                'extraction_id': ext.id,
                'title': f'Paper #{ext.study_id}: Título del documento',  # Mock
                'authors': 'Autor et al.',
                'status': ext.status,
                'researcher_id': researcher_id,
                'researcher_name': researcher_name,
                'progress': progress,
                'pdf_url': f'/static/pdfs/paper_{ext.study_id}.pdf'  # Mock URL
            })
        
        return papers
    
    def _serialize_papers(self, papers):
        """Serializa lista de papers"""
        if isinstance(papers, list) and len(papers) > 0 and isinstance(papers[0], dict):
            return papers
        return []
    
    def _serialize_tags(self, tags):
        """Serializa lista de tags"""
        result = []
        for tag in tags:
            result.append({
                'id': tag.id,
                'name': tag.name,
                'color': tag.color or '#6b7280',
                'type': tag.type,
                'is_mandatory': tag.is_mandatory,
                'is_public': tag.is_public,
                'approval_status': tag.approval_status,
                'question_id': tag.question_id,
                'created_by_id': tag.created_by_id,
                'quote_count': tag.quotes.count() if hasattr(tag, 'quotes') else 0
            })
        return result
    
    def _serialize_quotes(self, quotes):
        """Serializa lista de quotes"""
        result = []
        for quote in quotes:
            result.append({
                'id': quote.id,
                'extraction_id': quote.paper_extraction_id,
                'text_portion': quote.text_portion,
                'location': quote.location or '',
                'tags': [{'id': t.id, 'name': t.name, 'color': t.color} for t in quote.tags.all()],
                'researcher_id': quote.researcher_id,
                'validated': quote.validated,
                'comment': '',  # Obtener de Comment model si existe
                'created_at': quote.created_at.isoformat()
            })
        return result
    
    def _get_all_quotes(self, project_id):
        """Obtiene todas las quotes del proyecto"""
        return Quote.objects.filter(
            paper_extraction__project_id=project_id
        ).prefetch_related('tags').order_by('-created_at')


# =============================================================================
# API Views
# =============================================================================

@method_decorator(csrf_exempt, name='dispatch')
class QuoteAPIView(View):
    """API para gestionar quotes"""
    
    def post(self, request):
        """Crear nueva quote"""
        try:
            data = json.loads(request.body)
            extraction_service = ExtractionService()
            
            quote = extraction_service.create_quote(
                extraction_id=data['extraction_id'],
                researcher_id=data.get('researcher_id', 1),
                text_portion=data['text_portion'],
                location=data.get('location', ''),
                tag_names=data.get('tag_names', []),
                new_inductive_tag=data.get('new_inductive_tag')
            )
            
            return JsonResponse({
                'id': quote.id,
                'extraction_id': quote.paper_extraction_id,
                'text_portion': quote.text_portion,
                'location': quote.location,
                'tags': [{'id': t.id, 'name': t.name, 'color': t.color} for t in quote.tags.all()],
                'researcher_id': quote.researcher_id,
                'created_at': quote.created_at.isoformat()
            }, status=201)
            
        except BusinessRuleViolation as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def delete(self, request, quote_id):
        """Eliminar quote"""
        try:
            quote = Quote.objects.get(id=quote_id)
            quote.delete()
            return JsonResponse({'success': True})
        except Quote.DoesNotExist:
            return JsonResponse({'error': 'Quote not found'}, status=404)


@method_decorator(csrf_exempt, name='dispatch')
class TagAPIView(View):
    """API para gestionar tags"""
    
    def patch(self, request, tag_id):
        """Actualizar tag"""
        try:
            data = json.loads(request.body)
            tag = Tag.objects.get(id=tag_id)
            
            if 'name' in data:
                tag.name = data['name']
            if 'color' in data:
                tag.color = data['color']
            if 'justification' in data:
                tag.justification = data['justification']
            
            tag.save()
            
            return JsonResponse({
                'id': tag.id,
                'name': tag.name,
                'color': tag.color,
                'type': tag.type,
                'is_mandatory': tag.is_mandatory
            })
            
        except Tag.DoesNotExist:
            return JsonResponse({'error': 'Tag not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def delete(self, request, tag_id):
        """Eliminar tag"""
        try:
            tag = Tag.objects.get(id=tag_id)
            tag.delete()
            return JsonResponse({'success': True})
        except Tag.DoesNotExist:
            return JsonResponse({'error': 'Tag not found'}, status=404)


@method_decorator(csrf_exempt, name='dispatch')
class TagApproveView(View):
    """API para aprobar tags"""
    
    def post(self, request, tag_id):
        try:
            tag_service = TagService()
            tag = tag_service.approve_tag(tag_id, owner_id=1)
            return JsonResponse({
                'id': tag.id,
                'approval_status': tag.approval_status,
                'is_public': tag.is_public
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class TagRejectView(View):
    """API para rechazar tags"""
    
    def post(self, request, tag_id):
        try:
            tag_service = TagService()
            tag = tag_service.reject_tag(tag_id, owner_id=1)
            return JsonResponse({
                'id': tag.id,
                'approval_status': tag.approval_status,
                'is_public': tag.is_public
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class PhaseActivateView(View):
    """API para activar la fase de extracción"""
    
    def post(self, request):
        try:
            data = json.loads(request.body) if request.body else {}
            project_id = data.get('project_id', 1)
            
            phase_service = ExtractionPhaseService()
            
            # Mock: papers y researchers
            paper_ids = list(range(1, 7))  # Papers 1-6
            researcher_ids = [10, 20, 30]  # Juan, Ana, Pedro
            
            phase = phase_service.activate_phase(
                project_id=project_id,
                owner_id=1,
                paper_ids=paper_ids,
                researcher_ids=researcher_ids
            )
            
            return JsonResponse({
                'status': phase.status,
                'activated_at': phase.activated_at.isoformat() if phase.activated_at else None
            })
            
        except BusinessRuleViolation as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch') 
class ExtractionCompleteView(View):
    """API para marcar extracción como completa"""
    
    def post(self, request, extraction_id):
        try:
            extraction_service = ExtractionService()
            extraction = extraction_service.complete_extraction(
                extraction_id=extraction_id,
                user_id=request.GET.get('user_id', 1)
            )
            return JsonResponse({
                'id': extraction.id,
                'status': extraction.status,
                'completed_at': extraction.completed_at.isoformat() if extraction.completed_at else None
            })
        except BusinessRuleViolation as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
