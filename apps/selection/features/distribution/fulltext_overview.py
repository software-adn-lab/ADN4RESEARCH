"""
Vistas para Fulltext Overview.
Gestión de PDFs y distribución para fulltext review.
"""
import logging

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib import messages
from django.core.files.storage import default_storage

from apps.project.structure.models.project_models import Project, Membership
from apps.project.facade import get_project_facade
from apps.selection.features.distribution.models import SelectionPhase
from apps.selection.features.screening.models import PaperAssignment, PaperReview
from apps.selection.models.choices import (
    SelectionDecisionChoices,
    AssignmentStageChoices,
    SubPhaseStatusChoices,
    SelectionStageChoices,
)
from apps.selection.features.distribution.services import FulltextDistributionService
from apps.selection.features.discussion.services import DiscrepancyResolutionService

logger = logging.getLogger(__name__)


def _count_pdf_pages(pdf_path: str) -> int:
    """
    Count pages in a PDF file stored in default_storage (S3 or local).
    Returns 0 if unable to count.
    """
    if not pdf_path:
        return 0
    
    try:
        from pypdf import PdfReader
        from io import BytesIO
        from django.conf import settings
        
        pdf_content = None
        
        # Check if using S3
        use_s3 = getattr(settings, 'USE_S3', False) or hasattr(settings, 'AWS_STORAGE_BUCKET_NAME')
        
        if use_s3 and hasattr(settings, 'AWS_STORAGE_BUCKET_NAME'):
            # Use boto3 directly for S3
            import boto3
            from botocore.config import Config
            
            s3_config = Config(signature_version='s3v4')
            s3_client = boto3.client(
                's3',
                endpoint_url=getattr(settings, 'AWS_S3_ENDPOINT_URL', None),
                aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
                aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
                region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1'),
                config=s3_config,
                verify=getattr(settings, 'AWS_S3_VERIFY', True),
            )
            
            bucket = settings.AWS_STORAGE_BUCKET_NAME
            response = s3_client.get_object(Bucket=bucket, Key=pdf_path)
            pdf_content = response['Body'].read()
        else:
            # Use default storage for local files
            with default_storage.open(pdf_path, 'rb') as pdf_file:
                pdf_content = pdf_file.read()
        
        # Count pages
        reader = PdfReader(BytesIO(pdf_content))
        return len(reader.pages)
    except Exception as e:
        logger.warning(f"Could not count PDF pages for {pdf_path}: {e}")
        return 0


def _calculate_fulltext_progress(selection_phase, user):
    """Calculate fulltext review progress for a user"""
    assignments = PaperAssignment.objects.filter(
        selection_phase=selection_phase,
        researcher=user,
        stage=AssignmentStageChoices.FULLTEXT,
        is_third_reviewer=False
    )
    
    total = assignments.count()
    
    if total == 0:
        return {
            'total': 0,
            'pending': 0,
            'included': 0,
            'excluded': 0,
            'percentage': 0,
            'pending_pct': 0,
            'included_pct': 0,
            'excluded_pct': 0
        }
    
    reviews = PaperReview.objects.filter(
        assignment__in=assignments,
        stage='FULL_TEXT'
    )
    
    included = reviews.filter(decision=SelectionDecisionChoices.INCLUDED).count()
    excluded = reviews.filter(decision=SelectionDecisionChoices.EXCLUDED).count()
    reviewed = included + excluded
    pending = total - reviewed
    
    percentage = int((reviewed / total) * 100)
    pending_pct = int((pending / total) * 100)
    included_pct = int((included / total) * 100)
    excluded_pct = 100 - pending_pct - included_pct
    
    return {
        'total': total,
        'pending': pending,
        'included': included,
        'excluded': excluded,
        'percentage': percentage,
        'pending_pct': pending_pct,
        'included_pct': included_pct,
        'excluded_pct': excluded_pct
    }


def _get_fulltext_team_progress(selection_phase, exclude_user):
    """Get fulltext progress for all team members"""
    researchers = Membership.objects.filter(
        project=selection_phase.project,
        role__in=['OWNER', 'RESEARCHER']
    ).select_related('user').exclude(user=exclude_user)
    
    team_progress = []
    for membership in researchers:
        progress = _calculate_fulltext_progress(selection_phase, membership.user)
        progress['researcher'] = membership.user
        team_progress.append(progress)
    
    return team_progress


def _get_included_papers_from_screening(selection_phase):
    """
    Get papers that were included in screening phase.
    """
    from apps.selection.features.discussion.models import ConflictResolution
    
    included_papers = set()
    
    # 1. Get papers from resolved conflicts with INCLUDED
    resolved_included = ConflictResolution.objects.filter(
        selection_phase=selection_phase,
        stage=AssignmentStageChoices.SCREENING,
        is_resolved=True,
        final_decision=SelectionDecisionChoices.INCLUDED
    ).values_list('paper_id', flat=True)
    
    included_papers.update(resolved_included)
    
    # 2. Get papers where all reviews are INCLUDED (no conflict)
    all_screening_assignments = PaperAssignment.objects.filter(
        selection_phase=selection_phase,
        stage=AssignmentStageChoices.SCREENING,
        is_third_reviewer=False
    )
    
    paper_ids = all_screening_assignments.values_list('paper_id', flat=True).distinct()
    
    for paper_id in paper_ids:
        if paper_id in included_papers:
            continue
        
        # Check if in unresolved conflict
        has_unresolved = ConflictResolution.objects.filter(
            selection_phase=selection_phase,
            stage=AssignmentStageChoices.SCREENING,
            paper_id=paper_id,
            is_resolved=False
        ).exists()
        
        if has_unresolved:
            continue
        
        # Get all reviews for this paper
        reviews = PaperReview.objects.filter(
            assignment__selection_phase=selection_phase,
            assignment__paper_id=paper_id,
            assignment__stage=AssignmentStageChoices.SCREENING,
            stage='SCREENING'
        ).exclude(decision=SelectionDecisionChoices.PENDING)
        
        if not reviews.exists():
            continue
        
        decisions = set(reviews.values_list('decision', flat=True))
        if decisions == {SelectionDecisionChoices.INCLUDED}:
            included_papers.add(paper_id)
    
    return list(included_papers)


@login_required
def fulltext_overview(request, project_id):
    """
    Fulltext Overview - PDF management and distribution by page count.
    Shows your progress, team progress, and list of included papers with PDF status.
    """
    project = get_object_or_404(Project, id=project_id)
    selection_phase = get_object_or_404(SelectionPhase, project=project)
    
    # Check if fulltext phase is accessible
    if not selection_phase.can_access_fulltext():
        messages.warning(request, 'Complete screening phase first (including all discussions) to access full-text review.')
        return redirect('selection:screening_overview', project_id=project_id)
    
    is_owner = request.user == project.owner
    
    # Determine phase mode
    if selection_phase.fulltext_status == SubPhaseStatusChoices.COMPLETED:
        phase_mode = 'finalizado'
    else:
        phase_mode = 'en_curso'
    
    # Get user progress (only if distributed)
    user_progress = _calculate_fulltext_progress(selection_phase, request.user)
    
    # Get team progress
    team_progress = _get_fulltext_team_progress(selection_phase, request.user)
    
    # Get included papers from screening
    included_paper_ids = _get_included_papers_from_screening(selection_phase)
    
    # Get paper metadata and PDF status
    project_facade = get_project_facade()
    papers_data = []
    total_papers = 0
    papers_with_pdf = 0
    papers_without_pdf = 0
    total_pages = 0
    
    if included_paper_ids:
        all_studies = project_facade.get_studies_by_project(
            project_id=project_id,
            include_metadata=True
        )
        studies_by_id = {str(s['id']): s for s in all_studies}
        
        # Get page_count directly from StudyModel (since facade doesn't return it)
        study_models_by_id = {}
        try:
            from apps.acquisition.models import StudyModel
            study_models = StudyModel.objects.filter(uuid__in=included_paper_ids).values(
                'uuid',
                'page_count',
                'pdf_path',
                'title',
                'authors',
                'year'
            )
            study_models_by_id = {str(sm['uuid']): sm for sm in study_models}
        except Exception:
            pass
        
        for paper_id in included_paper_ids:
            study = studies_by_id.get(paper_id, {})
            
            # Get page_count and pdf_path from direct model query
            model_data = study_models_by_id.get(paper_id, {})
            if not study:
                study = {
                    'title': model_data.get('title') or paper_id,
                    'authors': model_data.get('authors') or 'N/A',
                    'year': model_data.get('year'),
                    'pdf_path': model_data.get('pdf_path'),
                }
            pdf_path = model_data.get('pdf_path') or study.get('pdf_path')
            pdf_url = None
            page_count = model_data.get('page_count')
            
            # If page_count not stored, calculate from PDF
            if pdf_path and not page_count:
                page_count = _count_pdf_pages(pdf_path)
            
            page_count = page_count or 0
            
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
    
    # Sort by title
    papers_data.sort(key=lambda x: x['title'].lower())
    
    # Check for conflicts
    discrepancy_service = DiscrepancyResolutionService(selection_phase)
    conflicts = discrepancy_service.get_conflicts(stage='FULL_TEXT')
    conflicts_count = len(conflicts)
    
    # Check if all reviews are complete
    all_reviews_complete = True
    fulltext_assignments = PaperAssignment.objects.filter(
        selection_phase=selection_phase,
        stage=AssignmentStageChoices.FULLTEXT,
        is_third_reviewer=False
    )
    
    if fulltext_assignments.exists():
        for assignment in fulltext_assignments:
            review = PaperReview.objects.filter(
                assignment=assignment,
                stage='FULL_TEXT'
            ).first()
            if not review or review.decision == SelectionDecisionChoices.PENDING:
                all_reviews_complete = False
                break
    else:
        all_reviews_complete = False
    
    context = {
        'project': project,
        'selection_phase': selection_phase,
        'is_owner': is_owner,
        'papers': papers_data,
        'total_papers': total_papers,
        'papers_with_pdf': papers_with_pdf,
        'papers_without_pdf': papers_without_pdf,
        'total_pages': total_pages,
        'user_progress': user_progress,
        'team_progress': team_progress,
        'current_stage': 'fulltext_overview',
        'phase_mode': phase_mode,
        'conflicts_count': conflicts_count,
        'all_reviews_complete': all_reviews_complete,
        'can_finalize': all_reviews_complete and conflicts_count == 0 and selection_phase.fulltext_distributed,
    }
    
    return render(request, 'fulltext_overview/overview.html', context)


@login_required
@require_http_methods(['POST'])
def distribute_fulltext_papers(request, project_id):
    """
    Execute fulltext distribution algorithm (by PDF page count).
    """
    project = get_object_or_404(Project, id=project_id)
    
    if request.user != project.owner:
        messages.error(request, 'Only project owner can distribute papers')
        return redirect('selection:fulltext_overview', project_id=project_id)
    
    selection_phase = get_object_or_404(SelectionPhase, project=project)
    
    if not selection_phase.can_access_fulltext():
        messages.error(request, 'Complete screening phase first')
        return redirect('selection:screening_overview', project_id=project_id)
    
    try:
        reviews_per_paper = int(request.POST.get('reviews_per_paper', 2))
        if reviews_per_paper not in [2, 3, 4]:
            reviews_per_paper = 2
        
        # Execute distribution
        service = FulltextDistributionService(project_id, selection_phase)
        distribution = service.distribute_papers(total_reviews_per_paper=reviews_per_paper)
        
        # Clear existing fulltext assignments
        PaperAssignment.objects.filter(
            selection_phase=selection_phase,
            stage=AssignmentStageChoices.FULLTEXT
        ).delete()
        
        # Clear existing fulltext reviews
        PaperReview.objects.filter(
            assignment__selection_phase=selection_phase,
            stage='FULL_TEXT'
        ).delete()
        
        # Create new assignments
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        for username, paper_ids in distribution.items():
            researcher = User.objects.get(username=username)
            
            for paper_id in paper_ids:
                PaperAssignment.objects.create(
                    selection_phase=selection_phase,
                    paper_id=paper_id,
                    researcher=researcher,
                    stage=AssignmentStageChoices.FULLTEXT,
                    is_third_reviewer=False
                )
        
        # Update phase status
        selection_phase.fulltext_screening_status = SubPhaseStatusChoices.IN_PROGRESS
        selection_phase.current_stage = SelectionStageChoices.FULLTEXT_OVERVIEW
        selection_phase.save()
        
        messages.success(request, f'Papers distributed for full-text review! {len(distribution)} researchers assigned with {reviews_per_paper} reviews per paper.')
    
    except Exception as e:
        messages.error(request, f'Distribution failed: {str(e)}')
    
    return redirect('selection:fulltext_overview', project_id=project_id)


@login_required
@require_http_methods(['POST'])
def download_overview_pdfs(request, project_id):
    """
    Download PDFs for all included papers.
    """
    project = get_object_or_404(Project, id=project_id)
    selection_phase = get_object_or_404(SelectionPhase, project=project)
    
    included_paper_ids = _get_included_papers_from_screening(selection_phase)
    
    if not included_paper_ids:
        return JsonResponse({"ok": True, "message": "No studies to process", "result": {}}, status=200)
    
    try:
        from apps.acquisition.facade import get_acquisition_facade
        acquisition_facade = get_acquisition_facade()
        
        result = acquisition_facade.download_fulltexts(included_paper_ids)
        
        # Get updated status
        statuses = acquisition_facade.get_study_status(included_paper_ids)
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
@require_http_methods(['POST'])
def upload_overview_pdf(request, project_id):
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


@login_required
@require_http_methods(['POST'])
def send_fulltext_reminder(request, project_id):
    """
    Send reminder notification for fulltext review.
    """
    project = get_object_or_404(Project, id=project_id)
    
    if request.user != project.owner:
        messages.error(request, 'Only project owner can send reminders')
        return redirect('selection:fulltext_overview', project_id=project_id)
    
    researcher_id = request.POST.get('researcher_id')
    if not researcher_id:
        messages.error(request, 'No researcher specified')
        return redirect('selection:fulltext_overview', project_id=project_id)
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        researcher = User.objects.get(id=researcher_id)
        
        from apps.notification.models import Notification
        Notification.objects.create(
            recipient=researcher,
            sender=request.user,
            type='REMINDER',
            title='Full-text Review Reminder',
            custom_message=f'You have pending papers to review in the full-text phase of project "{project.title}". Please complete your reviews.',
            project=project
        )
        messages.success(request, f'Reminder sent to {researcher.get_full_name() or researcher.username}')
            
    except User.DoesNotExist:
        messages.error(request, 'Researcher not found')
    except Exception as e:
        messages.error(request, f'Failed to send notification: {str(e)}')
    
    return redirect('selection:fulltext_overview', project_id=project_id)


@login_required
@require_http_methods(['POST'])
def finalize_fulltext(request, project_id):
    """
    Finalize fulltext phase.
    Only possible when all reviews are complete and all conflicts are resolved.
    """
    project = get_object_or_404(Project, id=project_id)
    
    if request.user != project.owner:
        messages.error(request, 'Only project owner can finalize full-text phase')
        return redirect('selection:fulltext_overview', project_id=project_id)
    
    selection_phase = get_object_or_404(SelectionPhase, project=project)
    
    # Check for unresolved conflicts
    discrepancy_service = DiscrepancyResolutionService(selection_phase)
    conflicts = discrepancy_service.get_conflicts(stage='FULL_TEXT')
    
    if conflicts:
        messages.error(request, f'Cannot finalize: {len(conflicts)} unresolved conflicts remain.')
        return redirect('selection:fulltext_overview', project_id=project_id)
    
    # Check for pending reviews
    all_assignments = PaperAssignment.objects.filter(
        selection_phase=selection_phase,
        stage=AssignmentStageChoices.FULLTEXT,
        is_third_reviewer=False
    )
    
    for assignment in all_assignments:
        review = PaperReview.objects.filter(
            assignment=assignment,
            stage='FULL_TEXT'
        ).first()
        if not review or review.decision == SelectionDecisionChoices.PENDING:
            messages.error(request, 'Cannot finalize: Some reviews are still pending.')
            return redirect('selection:fulltext_overview', project_id=project_id)
    
    # Finalize fulltext
    selection_phase.fulltext_screening_status = SubPhaseStatusChoices.COMPLETED
    selection_phase.discussion_fulltext_status = SubPhaseStatusChoices.COMPLETED
    selection_phase.status = 'FINALIZED'
    selection_phase.save()
    
    # Count approved papers
    from apps.selection.services import get_selection_facade
    facade = get_selection_facade()
    approved_count = len(facade.get_approved_fulltext_papers(project_id))
    
    messages.success(request, f'Selection phase completed! {approved_count} papers approved for extraction.')
    return redirect('selection:fulltext_overview', project_id=project_id)
