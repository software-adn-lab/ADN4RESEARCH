from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpResponseForbidden, JsonResponse
from django.core.files.storage import default_storage

from apps.project.structure.models.project_models import Project
from apps.project.facade import get_project_facade
from apps.selection.models import (
    SelectionPhase, 
    PaperReview,
    SelectionStageChoices, 
    SelectionDecisionChoices
)


@login_required
def fulltext_overview(request, project_id):
    """
    Vista de Full-text Overview: muestra todos los papers incluidos de todos los miembros
    en la fase de screening, con información sobre descarga de PDFs.
    Esta vista es para gestionar PDFs antes de la fase de full-text screening.
    """
    project = get_object_or_404(Project, id=project_id)
    
    # Verificar que el usuario es miembro del proyecto
    if not project.memberships.filter(user=request.user).exists():
        return HttpResponseForbidden("No tienes acceso a este proyecto")
    
    # Obtener la fase de selección
    selection_phase = get_object_or_404(SelectionPhase, project=project)
    
    # Obtener todos los papers que fueron incluidos en la fase de screening
    # de TODOS los miembros (no solo del usuario actual)
    # Un paper puede ser incluido por múltiples researchers, pero solo contamos una vez
    included_reviews = PaperReview.objects.filter(
        assignment__selection_phase=selection_phase,
        stage=SelectionStageChoices.SCREENING,
        decision=SelectionDecisionChoices.INCLUDED
    ).select_related('assignment')
    
    # Obtener IDs únicos de papers desde los assignments (paper_id es el UUID del study)
    paper_ids_set = set()
    for review in included_reviews:
        paper_ids_set.add(str(review.assignment.paper_id))
    
    paper_ids = list(paper_ids_set)
    
    # Obtener estado de PDFs desde acquisition facade
    status_by_id = {}
    if paper_ids:
        from apps.acquisition.facade import get_acquisition_facade
        acquisition_facade = get_acquisition_facade()
        try:
            statuses = acquisition_facade.get_study_status(paper_ids)
            status_by_id = {
                str(s.get('id') or s.get('study_id') or s.get('uuid') or s.get('pk')): s 
                for s in statuses
            }
        except Exception:
            pass  # Si falla, status_by_id queda vacío
    
    # Obtener metadatos de estudios desde Project Facade
    project_facade = get_project_facade()
    papers_data = []
    total_papers = 0
    papers_with_pdf = 0
    papers_without_pdf = 0
    total_pages = 0
    
    if paper_ids:
        all_studies = project_facade.get_studies_by_project(
            project_id=project_id,
            include_metadata=True
        )
        studies_by_id = {str(s['id']): s for s in all_studies}
        
        for paper_id in paper_ids:
            study = studies_by_id.get(paper_id)
            if not study:
                continue
            
            # Obtener estado de PDF
            st = status_by_id.get(paper_id, {})
            pdf_path = st.get('pdf_path') or study.get('pdf_path')
            pdf_url = None
            page_count = st.get('page_count', 0) or study.get('page_count', 0)
            
            if pdf_path:
                try:
                    pdf_url = default_storage.url(pdf_path)
                except Exception:
                    pdf_url = None
            
            has_pdf = bool(pdf_path)
            
            papers_data.append({
                'id': paper_id,
                'title': study.get('title', 'N/A'),
                'authors': study.get('authors', 'N/A'),
                'year': study.get('year'),
                'has_pdf': has_pdf,
                'page_count': page_count,
                'pdf_url': pdf_url,
            })
            
            total_papers += 1
            if has_pdf:
                papers_with_pdf += 1
                total_pages += page_count or 0
            else:
                papers_without_pdf += 1
    
    # Ordenar por título
    papers_data.sort(key=lambda x: x['title'].lower())
    
    context = {
        'project': project,
        'selection_phase': selection_phase,
        'papers': papers_data,
        'total_papers': total_papers,
        'papers_with_pdf': papers_with_pdf,
        'papers_without_pdf': papers_without_pdf,
        'total_pages': total_pages,
        'active': 'fulltext_overview',
    }
    
    return render(request, 'fulltext_overview/overview.html', context)


@login_required
@require_http_methods(["POST"])
def download_overview_pdfs(request, project_id):
    """
    Descargar PDFs para todos los papers incluidos en screening.
    Esta función descarga PDFs para TODOS los papers incluidos (de todos los miembros).
    """
    project = get_object_or_404(Project, id=project_id)
    selection_phase = get_object_or_404(SelectionPhase, project=project)
    
    # Obtener todos los papers incluidos de todos los miembros
    included_reviews = PaperReview.objects.filter(
        assignment__selection_phase=selection_phase,
        stage=SelectionStageChoices.SCREENING,
        decision=SelectionDecisionChoices.INCLUDED
    )
    
    # Obtener IDs únicos
    paper_ids_set = set()
    for review in included_reviews:
        paper_ids_set.add(str(review.assignment.paper_id))
    
    study_ids = list(paper_ids_set)
    
    if not study_ids:
        return JsonResponse({"ok": True, "message": "No studies to process", "result": {}}, status=200)
    
    from apps.acquisition.facade import get_acquisition_facade
    acquisition_facade = get_acquisition_facade()
    
    try:
        result = acquisition_facade.download_fulltexts(study_ids)
        # Adjuntar urls cuando existan
        statuses = acquisition_facade.get_study_status(study_ids)
        for st in statuses:
            path = st.get('pdf_path')
            st['pdf_url'] = default_storage.url(path) if path else None
        
        # Serializar DTO DownloadStatusResult a dict JSON-serializable
        result_dict = {
            "total_count": getattr(result, 'total_count', 0),
            "downloaded_count": getattr(result, 'downloaded_count', 0),
            "available_count": getattr(result, 'available_count', 0),
            "failed_count": getattr(result, 'failed_count', 0),
        }
        return JsonResponse({"ok": True, "result": result_dict, "statuses": statuses})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def upload_overview_pdf(request, project_id):
    """
    Subir manualmente un PDF para un estudio.
    Campos esperados: study_id (UUID), file (UploadedFile)
    """
    study_id = request.POST.get('study_id')
    file_obj = request.FILES.get('file')
    
    if not study_id or not file_obj:
        return JsonResponse({"ok": False, "error": "study_id and file are required"}, status=400)
    
    from apps.acquisition.facade import get_acquisition_facade
    acquisition_facade = get_acquisition_facade()
    
    try:
        upload_res = acquisition_facade.upload_study_pdf(
            study_id=study_id, 
            file_obj=file_obj, 
            filename=file_obj.name, 
            user=request.user
        )
        pdf_url = default_storage.url(upload_res.get('pdf_path')) if upload_res.get('pdf_path') else None
        return JsonResponse({"ok": True, "result": upload_res, "pdf_url": pdf_url})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
