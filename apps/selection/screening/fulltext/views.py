"""
Vistas para screening de texto completo.
Responsable de la revisión PDF de papers incluidos en screening.
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse

from apps.project.structure.models.project_models import Project
from django.core.files.storage import default_storage
from apps.selection.models import (
    SelectionPhase, PaperReview,
    SelectionStageChoices, SelectionDecisionChoices
)
from apps.project.facade import get_project_facade


@login_required
def fulltext_view(request, project_id):
    """
    Página de screening de texto completo.
    
    Obtiene los papers INCLUIDOS del screening de metadatos
    y consulta el estado actual de sus PDFs (sin descargar automáticamente).
    """
    project = get_object_or_404(Project, id=project_id)
    selection_phase = get_object_or_404(SelectionPhase, project=project)

    # Obtener reviews INCLUIDAS de la etapa de screening de metadatos SOLO del usuario actual
    included_reviews = PaperReview.objects.filter(
        assignment__selection_phase=selection_phase,
        assignment__researcher=request.user,
        stage=SelectionStageChoices.SCREENING,
        decision=SelectionDecisionChoices.INCLUDED
    )

    # IDs de estudios desde assignments (PaperAssignment usa paper_id, no FK a study)
    paper_ids = [str(review.assignment.paper_id) for review in included_reviews]

    status_by_id = {}
    if paper_ids:
        from apps.acquisition.facade import get_acquisition_facade
        acquisition_facade = get_acquisition_facade()
        try:
            # Solo consultar estado actual de PDFs (sin descargar)
            statuses = acquisition_facade.get_study_status(paper_ids)
            status_by_id = {str(s.get('id') or s.get('study_id') or s.get('uuid') or s.get('pk')): s for s in statuses}
        except Exception as e:
            pass  # Si falla, status_by_id queda vacío

    # Obtener metadatos de estudios desde Project Facade
    project_facade = get_project_facade()
    papers = []
    if paper_ids:
        all_studies = project_facade.get_studies_by_project(
            project_id=project_id,
            include_metadata=True
        )
        studies_by_id = {str(s['id']): s for s in all_studies}

        for review in included_reviews:
            pid = str(review.assignment.paper_id)
            study = studies_by_id.get(pid)
            if not study:
                continue

            # Buscar si ya hay una revisión en FULL_TEXT para este assignment
            fulltext_review = PaperReview.objects.filter(
                assignment=review.assignment,
                stage=SelectionStageChoices.FULL_TEXT
            ).first()

            # Enriquecer con estado de PDF si está disponible
            st = status_by_id.get(pid, {})
            pdf_path = st.get('pdf_path') or study.get('pdf_path')
            pdf_url = None
            if pdf_path:
                try:
                    pdf_url = default_storage.url(pdf_path)
                except Exception:
                    pdf_url = None

            papers.append({
                'assignment': review.assignment,
                'study': study,
                'review_screening': review,
                'review_fulltext': fulltext_review,
                'pdf_path': pdf_path,
                'pdf_url': pdf_url,
            })

    context = {
        'project': project,
        'selection_phase': selection_phase,
        'papers': papers,
        'current_stage': 'fulltext'
    }

    return render(request, 'screening/fulltext/fulltext.html', context)


@login_required
@require_http_methods(["POST"])
def retry_fulltext_downloads(request, project_id):
    """
    Reintentar descarga de PDFs para uno o varios estudios.
    - Si se envía study_ids (POST JSON o form), usa esos IDs
    - Si no, usa los INCLUIDOS del screening del usuario actual
    """
    project = get_object_or_404(Project, id=project_id)
    selection_phase = get_object_or_404(SelectionPhase, project=project)

    # Leer study_ids desde POST (puede venir como lista o CSV)
    study_ids = request.POST.getlist('study_ids') or []
    if not study_ids:
        raw = request.POST.get('study_ids')
        if raw:
            study_ids = [s.strip() for s in raw.split(',') if s.strip()]

    if not study_ids:
        included_reviews = PaperReview.objects.filter(
            assignment__selection_phase=selection_phase,
            assignment__researcher=request.user,
            stage=SelectionStageChoices.SCREENING,
            decision=SelectionDecisionChoices.INCLUDED
        )
        study_ids = [str(r.assignment.paper_id) for r in included_reviews]

    if not study_ids:
        return JsonResponse({"ok": True, "message": "No studies to process", "result": {}}, status=200)

    from apps.acquisition.facade import get_acquisition_facade
    acquisition_facade = get_acquisition_facade()
    try:
        result = acquisition_facade.download_fulltexts(study_ids)
        # Adjuntar urls cuando existan
        statuses = acquisition_facade.get_study_status(study_ids)
        from django.core.files.storage import default_storage
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
def upload_fulltext_pdf(request, project_id):
    """
    Subir manualmente un PDF para un estudio (paper_id).
    Campos esperados: study_id (UUID), file (UploadedFile)
    """
    study_id = request.POST.get('study_id')
    file_obj = request.FILES.get('file')
    if not study_id or not file_obj:
        return JsonResponse({"ok": False, "error": "study_id and file are required"}, status=400)

    from apps.acquisition.facade import get_acquisition_facade
    acquisition_facade = get_acquisition_facade()
    try:
        upload_res = acquisition_facade.upload_study_pdf(study_id=study_id, file_obj=file_obj, filename=file_obj.name, user=request.user)
        from django.core.files.storage import default_storage
        pdf_url = default_storage.url(upload_res.get('pdf_path')) if upload_res.get('pdf_path') else None
        return JsonResponse({"ok": True, "result": upload_res, "pdf_url": pdf_url})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
