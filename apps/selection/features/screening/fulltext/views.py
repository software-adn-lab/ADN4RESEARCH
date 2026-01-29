"""
Vistas para fulltext review (screening de PDFs).
Responsable de la revisión de papers completos.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib import messages
from django.core.files.storage import default_storage

from apps.project.structure.models.project_models import Project
from apps.project.facade import get_project_facade
from apps.design.api import get_design_protocol
from apps.selection.features.distribution.models import SelectionPhase
from apps.selection.features.screening.models import PaperAssignment, PaperReview
from apps.selection.models.choices import (
    SelectionDecisionChoices,
    AssignmentStageChoices,
    SubPhaseStatusChoices,
)


def _get_criteria(project_id):
    """Get inclusion/exclusion criteria from design"""
    protocol = get_design_protocol()
    
    def _normalize_criteria(criteria_list):
        normalized = []
        for c in criteria_list or []:
            cid = c.get('id') or c.get('uuid') or c.get('pk') or c.get('code') or c.get('slug')
            label = c.get('description') or c.get('text') or c.get('name') or c.get('title') or str(c)
            if cid and label:
                normalized.append({'id': str(cid), 'label': str(label)})
        return normalized
    
    try:
        inclusion_criteria = _normalize_criteria(protocol.get_inclusion_criteria(project_id))
    except Exception:
        inclusion_criteria = []
    try:
        exclusion_criteria = _normalize_criteria(protocol.get_exclusion_criteria(project_id))
    except Exception:
        exclusion_criteria = []
    
    # Extra exclusion criteria
    exclusion_extras = [
        {'id': 'NO_MATCH_INCLUSION', 'label': 'Estudio no aplicable para ningún criterio de inclusión'},
        {'id': 'OUT_OF_SCOPE', 'label': 'Estudio fuera de foco'},
    ]
    exclusion_criteria = exclusion_criteria + exclusion_extras
    
    return inclusion_criteria, exclusion_criteria


@login_required
def fulltext_view(request, project_id):
    """
    Fulltext Review - PDF-based paper review.
    
    Shows papers assigned to the current user for fulltext review.
    Papers must be distributed first (from fulltext_overview).
    """
    project = get_object_or_404(Project, id=project_id)
    selection_phase = get_object_or_404(SelectionPhase, project=project)

    if not selection_phase.is_selection_schedule_configured():
        messages.warning(request, 'Selection schedule is not configured yet.')
        return redirect('selection:screening_overview', project_id=project_id)

    if not selection_phase.is_fulltext_window_open():
        start_date = selection_phase.fulltext_screening_start_date
        start_label = start_date.date() if start_date else 'scheduled date'
        messages.warning(request, f'Full-text starts on {start_label}.')
        return redirect('selection:screening_overview', project_id=project_id)
    
    # Check if fulltext phase is accessible
    if not selection_phase.can_access_fulltext():
        messages.warning(request, 'Complete screening phase first to access full-text review.')
        return redirect('selection:screening_overview', project_id=project_id)
    
    # Check if papers are distributed
    if not selection_phase.fulltext_distributed:
        messages.info(request, 'Papers have not been distributed for full-text review yet.')
        return redirect('selection:fulltext_overview', project_id=project_id)
    
    # Get user's fulltext assignments
    assignments = PaperAssignment.objects.filter(
        selection_phase=selection_phase,
        researcher=request.user,
        stage=AssignmentStageChoices.FULLTEXT,
        is_third_reviewer=False
    )
    
    if not assignments.exists():
        messages.info(request, 'You have no papers assigned for full-text review.')
        return redirect('selection:fulltext_overview', project_id=project_id)
    
    paper_ids = [a.paper_id for a in assignments]
    
    # Get study metadata
    project_facade = get_project_facade()
    all_studies = project_facade.get_studies_by_project(
        project_id=project_id,
        include_metadata=True
    )
    studies_by_id = {str(s['id']): s for s in all_studies}
    
    # Get PDF status from acquisition
    status_by_id = {}
    try:
        from apps.acquisition.facade import get_acquisition_facade
        acquisition_facade = get_acquisition_facade()
        statuses = acquisition_facade.get_study_status(paper_ids)
        status_by_id = {str(s.get('id') or s.get('study_id') or s.get('uuid')): s for s in statuses}
    except Exception:
        pass
    
    # Get criteria
    inclusion_criteria, exclusion_criteria = _get_criteria(project_id)
    criterion_lookup = {c['id']: c['label'] for c in (inclusion_criteria + exclusion_criteria)}
    
    papers = []
    pending_count = 0
    
    for assignment in assignments:
        pid = str(assignment.paper_id)
        study = studies_by_id.get(pid, {})
        
        # Get PDF info
        st = status_by_id.get(pid, {})
        pdf_path = st.get('pdf_path') or study.get('pdf_path')
        pdf_url = None
        if pdf_path:
            try:
                pdf_url = default_storage.url(pdf_path)
            except Exception:
                pass
        
        # Get existing fulltext review
        review = PaperReview.objects.filter(
            assignment=assignment,
            stage='FULL_TEXT'
        ).first()
        
        if not review or review.decision == SelectionDecisionChoices.PENDING:
            pending_count += 1
        
        papers.append({
            'assignment': assignment,
            'study': study,
            'review': review,
            'pdf_path': pdf_path,
            'pdf_url': pdf_url,
        })
    
    # Sort: pending first
    papers = sorted(
        papers,
        key=lambda p: 0 if (not p['review'] or p['review'].decision == SelectionDecisionChoices.PENDING) else 1
    )
    
    context = {
        'project': project,
        'selection_phase': selection_phase,
        'papers': papers,
        'pending_count': pending_count,
        'current_stage': 'fulltext_review',
        'inclusion_criteria': inclusion_criteria,
        'exclusion_criteria': exclusion_criteria,
        'criterion_lookup': criterion_lookup,
    }
    
    return render(request, 'screening/fulltext/fulltext.html', context)


@login_required
@require_http_methods(['POST'])
def submit_fulltext_review(request, project_id, assignment_id):
    """
    Submit a fulltext review decision.
    """
    assignment = get_object_or_404(PaperAssignment, id=assignment_id)
    
    # Verify user owns this assignment
    if assignment.researcher != request.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Verify it's a fulltext assignment
    if assignment.stage != AssignmentStageChoices.FULLTEXT:
        return JsonResponse({'error': 'Invalid assignment stage'}, status=400)
    
    notes = request.POST.get('notes', '')
    criterion_id = request.POST.get('criterion_id') or None
    criterion_label = request.POST.get('criterion_label') or None
    decision = request.POST.get('decision')
    
    if decision not in ['INCLUDED', 'EXCLUDED', 'PENDING']:
        return JsonResponse({'error': 'Invalid decision'}, status=400)
    
    # If decision is include/exclude, criterion is required
    if decision in [SelectionDecisionChoices.INCLUDED, SelectionDecisionChoices.EXCLUDED] and not criterion_id:
        return JsonResponse({'error': 'Criterion is required for this decision'}, status=400)
    
    review, created = PaperReview.objects.update_or_create(
        assignment=assignment,
        stage='FULL_TEXT',
        defaults={
            'decision': decision,
            'notes': notes,
            'criterion_label': criterion_label,
            'criterion_id': criterion_id
        }
    )
    
    return JsonResponse({
        'success': True,
        'review_id': review.id,
        'decision': decision,
        'criterion_id': criterion_id,
        'notes': notes
    })


@login_required
@require_http_methods(["POST"])
def retry_fulltext_downloads(request, project_id):
    """
    Retry downloading PDFs for specified studies.
    """
    project = get_object_or_404(Project, id=project_id)
    selection_phase = get_object_or_404(SelectionPhase, project=project)
    
    study_ids = request.POST.getlist('study_ids') or []
    if not study_ids:
        raw = request.POST.get('study_ids')
        if raw:
            study_ids = [s.strip() for s in raw.split(',') if s.strip()]
    
    if not study_ids:
        # Use user's assigned papers
        assignments = PaperAssignment.objects.filter(
            selection_phase=selection_phase,
            researcher=request.user,
            stage=AssignmentStageChoices.FULLTEXT
        )
        study_ids = [a.paper_id for a in assignments]
    
    if not study_ids:
        return JsonResponse({"ok": True, "message": "No studies to process", "result": {}}, status=200)
    
    try:
        from apps.acquisition.facade import get_acquisition_facade
        acquisition_facade = get_acquisition_facade()
        
        result = acquisition_facade.download_fulltexts(study_ids)
        
        statuses = acquisition_facade.get_study_status(study_ids)
        for st in statuses:
            path = st.get('pdf_path')
            st['pdf_url'] = default_storage.url(path) if path else None
        
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
    Upload PDF manually for a study.
    """
    study_id = request.POST.get('study_id')
    file_obj = request.FILES.get('file')
    
    if not study_id or not file_obj:
        return JsonResponse({"ok": False, "error": "study_id and file are required"}, status=400)
    
    try:
        from apps.acquisition.facade import get_acquisition_facade
        acquisition_facade = get_acquisition_facade()
        
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
