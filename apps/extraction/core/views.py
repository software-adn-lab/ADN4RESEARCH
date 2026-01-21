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
from apps.extraction.planning.models import ExtractionStatusChoices
from apps.extraction.shared.mixins import ProjectMemberRequiredMixin
from apps.extraction.shared.exceptions import BusinessRuleViolation
from apps.extraction.adapters.acquisition import get_acquisition_adapter

logger = logging.getLogger(__name__)


class PaperAccessMixin(UserPassesTestMixin):
    """
    Mixin to validate access to papers.
    
    Compatible with both DetailView (which has get_object())
    and simple View (which receives pk in get()).
    """
    
    def test_func(self):
        """
        Access rules:
        - Project Owner
        - Assigned Researcher
        - Staff/Superuser
        """
        # ✅ Attempt to get paper in different ways
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
        Get paper depending on the view type.
        """
        # If it's DetailView, use get_object()
        if hasattr(self, 'get_object'):
            return self.get_object()
        
        # If it's a simple View, get pk from kwargs
        pk = self.kwargs.get('pk')
        if pk:
            return get_object_or_404(PaperExtraction, pk=pk)
        
        # Could not retrieve the paper
        return None


class PaperDetailView(LoginRequiredMixin, ProjectMemberRequiredMixin, PaperAccessMixin, DetailView):
    """
    View for the paper extraction workspace.
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
        
        # Available tags
        context['available_tags'] = phase.tags.usable_by(
            self.request.user
        ).order_by('name')
        
        # Mandatory tags
        context['mandatory_tags'] = phase.tags.mandatory()
        
        # Sorted quotes
        quotes = paper.quotes.select_related('created_by').prefetch_related('tags').all()
        sorted_quotes = sorted(quotes, key=lambda q: q.location.get('page', 0))
        context['quotes'] = sorted_quotes

        # Serialize for JavaScript
        quote_dtos = [QuoteDTO.from_model(q) for q in sorted_quotes]
        context['quotes_json'] = json.dumps(
            [dto.to_dict() for dto in quote_dtos],
            cls=DjangoJSONEncoder
        )
        
        # URLs for JavaScript
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
    Serves PDF files securely.
    """
    
    def get(self, request, project_id, pk):
        """Serve PDF."""
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
        
        # Validate permissions (already validated by mixin, but explicit for clarity)
        if not self.test_func():
            logger.warning(f"Permission denied: user={request.user.username}, paper={pk}")
            raise PermissionDenied("You do not have permission to view this document.")
        
        # Get secure path
        file_path = self._get_safe_path(paper.path)
        
        if not file_path.exists():
            logger.error(f"PDF not found: {file_path}")
            raise Http404("The PDF file does not exist.")
        
        try:
            # Serve file
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
            raise Http404("Error serving the PDF file.")
    
    def _get_safe_path(self, relative_path):
        """
        Validate path against Path Traversal.
        """
        media_root = Path(settings.MEDIA_ROOT).resolve()
        absolute_path = (media_root / relative_path).resolve()
        
        try:
            absolute_path.relative_to(media_root)
        except ValueError:
            logger.error(
                f"Path traversal attempt: {relative_path} -> {absolute_path}"
            )
            raise PermissionDenied("Invalid file path.")
        
        return absolute_path
    
    def _sanitize_filename(self, filename):
        """Sanitize filename."""
        return (
            filename
            .replace('"', '')
            .replace("'", '')
            .replace('/', '-')
            .replace('\\', '-')
        )[:100]

class PaperCompleteView(LoginRequiredMixin, ProjectMemberRequiredMixin, PaperAccessMixin, View):
    """
    Endpoint to mark a paper as completed.
    
    Business Rules (delegated to Service):
    - Only owner or assigned researcher can complete
    - Must have at least one quote
    - All mandatory tags must be covered
    
    Architecture:
    - View: Permission validation and HTTP handling
    - Service: Business logic and orchestration
    - Model: Queries and persistence
    
    Reference Django CBV:
    https://docs.djangoproject.com/en/stable/ref/class-based-views/base/#view
    """
    
    def post(self, request, project_id, pk):
        """
        Process paper completion request.
        
        Args:
            request: HTTP request
            pk: Paper ID
            
        Returns:
            JsonResponse with result
        """
        paper = get_object_or_404(
            PaperExtraction,
            pk=pk,
            extraction_phase__project_id=project_id
        )
        
        # Validate permissions (view responsibility)
        if not self._can_complete_paper(request.user, paper):
            logger.warning(
                f"Permission denied: user={request.user.username}, "
                f"paper_id={paper.id}, action=complete"
            )
            return JsonResponse(
                {'error': 'You do not have permission to complete this paper.'},
                status=403
            )
        
        # Delegate business logic to service
        service = PaperExtractionService()
        
        try:
            # Service handles validations and transitions
            paper = service.attempt_complete_paper(paper, request.user)
            
            # Get summary for response
            summary = service.get_completion_summary(paper)
            
            paper_dto = PaperCompletionSummaryDTO(
                id=paper.id,
                status=paper.get_status_display(),
                quotes_count=summary['quotes_count'],
                coverage_percentage=summary['coverage_percentage']
            )

            return JsonResponse({
                'success': True,
                'message': '✅ Paper completed successfully',
                'paper': paper_dto.to_dict()
            })
            
        except BusinessRuleViolation as e:
            # Service raised business exception
            logger.info(
                f"Paper completion rejected: paper_id={paper.id}, "
                f"reason={str(e)}"
            )
            return JsonResponse(
                {'error': str(e)},
                status=400
            )
            
        except Exception as e:
            # Unexpected error
            logger.exception(
                f"Unexpected error completing paper: paper_id={paper.id}"
            )
            return JsonResponse(
                {'error': 'Internal Server Error'},
                status=500
            )
    
    def _can_complete_paper(self, user, paper):
        """
        Validate completion permissions.
        
        Note: This is permission validation (infrastructure),
        not business logic. That's why it's in the view.
        
        Args:
            user: Requesting user
            paper: Paper to complete
            
        Returns:
            bool: If permitted
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
    Endpoint to reopen a completed paper.
    """

    def post(self, request, project_id, pk):
        """
        Process reopen request.
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
                {'error': 'You do not have permission to reopen this paper.'},
                status=403
            )

        if paper.status == PaperExtractionStatusChoices.COMPLETED:
            paper.status = PaperExtractionStatusChoices.IN_PROGRESS
            paper.save(update_fields=['status', 'updated_at'])
            logger.info(f"Paper reopened: id={paper.id}, user={request.user.username}")
            return JsonResponse({
                'success': True,
                'message': 'Extraction reopened. You can now edit it again.'
            })
        
        return JsonResponse(
            {'error': 'The paper is not completed.'},
            status=400
        )

    def _can_reopen_paper(self, user, paper):
        """
        Validate reopen permissions. For now, same as completion.
        """
        project = paper.extraction_phase.project
        return (
            user == project.owner or
            paper.assigned_to == user or
            user.is_staff or
            user.is_superuser
        )


class QuoteCreateView(LoginRequiredMixin, ProjectMemberRequiredMixin, View):
    """API endpoint to create quotes (JSON)."""
    
    def post(self, request, project_id):
        try:
            # Parse data
            data = json.loads(request.body)
            
            # ✅ Debug logging
            logger.info("="*60)
            logger.info("QUOTE CREATE REQUEST")
            logger.info("="*60)
            logger.info(f"Request data: {data}")
            logger.info(f"User: {request.user.username}")
            
            # Get paper
            paper_id = data.get('paper_extraction_id')
            logger.info(f"Paper ID from request: {paper_id}")
            
            if not paper_id:
                logger.error("Missing paper_extraction_id")
                return JsonResponse(
                    {'error': 'paper_extraction_id is required'},
                    status=400
                )
            
            paper = get_object_or_404(PaperExtraction, pk=paper_id)
            logger.info(f"Paper found: {paper.id}")
            
            # Validate that phase is not CLOSED
            if paper.extraction_phase.status == ExtractionStatusChoices.CLOSED:
                logger.error("Extraction phase is closed, cannot create quotes")
                return JsonResponse(
                    {'error': 'The extraction phase is closed. Reopen the phase to continue.'},
                    status=403
                )
            
            # Validate permissions
            if not self._can_create_quote(request.user, paper):
                if paper.status == PaperExtractionStatusChoices.COMPLETED:
                    logger.error("Paper is completed, cannot create quotes")
                    return JsonResponse(
                        {'error': 'Cannot add quotes to a completed paper.'},
                        status=403
                    )
                logger.error("Permission denied")
                return JsonResponse(
                    {'error': 'You do not have permission to create quotes in this paper.'},
                    status=403
                )
            
            # ✅ Prepare form data
            form_data = {
                'text_fragment': data.get('text_fragment', ''),
                'paper_extraction': paper.id,
                'tags': data.get('tags', []),
            }
            
            logger.info(f"Form data: {form_data}")
            
            # Create form
            form = QuoteForm(form_data, paper=paper, user=request.user)
            
            # Validate
            if not form.is_valid():
                logger.error(f"Form validation failed: {form.errors}")
                return JsonResponse(
                    {
                        'error': 'Invalid data', 
                        'errors': form.errors.get_json_data()
                    },
                    status=400
                )
            
            # Save
            quote = form.save(commit=False)
            quote.created_by = request.user
            quote.location = data.get('location', {})
            quote.save()
            form.save_m2m()
            
            # ✅ Update paper status to IN_PROGRESS if it is PENDING
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
                {'error': 'Invalid JSON', 'detail': str(e)},
                status=400
            )
        except Exception as e:
            logger.exception("Unexpected error creating quote")
            return JsonResponse(
                {'error': 'Internal Server Error', 'detail': str(e)},
                status=500
            )
    
    def _can_create_quote(self, user, paper):
        """Validate creation permissions."""
        # Do not allow creating quotes in completed papers
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
    """API endpoint to delete quotes."""
    
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
                    {'error': 'Cannot delete quotes from a completed paper.'},
                    status=403
                )
            return JsonResponse(
                {'error': 'You do not have permission to delete this quote.'},
                status=403
            )
        
        try:
            quote_id = quote.id
            quote.delete()
            
            logger.info(f"Quote deleted: id={quote_id}, user={request.user.username}")
            
            return JsonResponse({
                'success': True,
                'message': 'Quote deleted successfully',
                'quote_id': quote_id
            })
            
        except Exception as e:
            logger.exception("Error deleting quote")
            return JsonResponse({'error': 'Error deleting the quote'}, status=500)
    
    def _can_delete_quote(self, user, quote):
        """Validate deletion permissions."""
        # Do not allow deleting quotes from completed papers
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
    View to reassign a paper to another project member.
    
    Only the project owner can reassign papers.
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
            # Get paper
            paper = get_object_or_404(PaperExtraction, pk=pk)
            phase = paper.extraction_phase
            project = phase.project
            
            # Validate user is owner
            if request.user != project.owner and not request.user.is_staff:
                return JsonResponse(
                    {'error': 'Only the owner can reassign papers.'},
                    status=403
                )
            
            # Get data
            data = json.loads(request.body)
            assigned_to_id = data.get('assigned_to_id')
            
            if not assigned_to_id:
                return JsonResponse(
                    {'error': 'assigned_to_id is required'},
                    status=400
                )
            
            # Get user to assign
            from django.contrib.auth import get_user_model
            User = get_user_model()
            assigned_user = get_object_or_404(User, pk=assigned_to_id)
            
            # Validate membership
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
                    {'error': f'{assigned_user.username} is not a project member.'},
                    status=400
                )
            
            # Reassign
            old_assigned_to = paper.assigned_to
            paper.assigned_to = assigned_user
            paper.save(update_fields=['assigned_to', 'updated_at'])
            
            logger.info(
                f"Paper {pk} reassigned from {old_assigned_to.username if old_assigned_to else 'nobody'} "
                f"to {assigned_user.username} by {request.user.username}"
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Paper reassigned to {assigned_user.username}',
                'assigned_to': {
                    'id': assigned_user.id,
                    'username': assigned_user.username
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse(
                {'error': 'Invalid JSON'},
                status=400
            )
        except Exception as e:
            logger.exception("Error reassigning paper")
            return JsonResponse(
                {'error': f'Error reassigning: {str(e)}'},
                status=500
            )

class PaperUpdatePDFView(LoginRequiredMixin, ProjectMemberRequiredMixin, PaperAccessMixin, View):
    """
    View to handle updating the PDF of a PaperExtraction.
    """
    def post(self, request, project_id, pk):
        paper = get_object_or_404(PaperExtraction, pk=pk, extraction_phase__project_id=project_id)

        # Check if extraction phase is closed
        if paper.extraction_phase.status == ExtractionStatusChoices.CLOSED:
            messages.error(
                request,
                'Cannot update PDF: the extraction phase is closed. Reopen the phase to continue.'
            )
            return redirect(request.META.get('HTTP_REFERER', '/'))

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
    Exports all quotes to CSV with full attributes.
    
    Includes:
    - Quote attributes (id, text_fragment, location, created_at, updated_at)
    - User who performed the extraction (created_by.username)
    - UUID and title of the study
    - Path of the paper_extraction
    - Tags associated with the quote
    """
    
    def get(self, request, project_id):
        """Exports extraction phase quotes to CSV."""
        try:
            # Get project extraction phase
            from apps.extraction.planning.models import ExtractionPhase
            phase = get_object_or_404(ExtractionPhase, project_id=project_id)
            
            # Get all phase quotes
            quotes = Quote.objects.filter(
                paper_extraction__extraction_phase=phase
            ).select_related(
                'paper_extraction',
                'paper_extraction__study',
                'created_by'
            ).prefetch_related('tags')
            
            # Create in-memory CSV file
            output = StringIO()
            writer = csv.writer(output, quoting=csv.QUOTE_ALL)
            
            # Write headers
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
            
            # Write data for each quote
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
            
            # Create HTTP response with the CSV
            csv_content = output.getvalue()
            response = HttpResponse(
                csv_content,
                content_type='text/csv; charset=utf-8'
            )
            response['Content-Disposition'] = 'attachment; filename="quotes_export.csv"'
            
            logger.info(
                f"User {request.user.username} exported {quotes.count()} quotes from project {project_id}"
            )
            
            return response
            
        except Exception as e:
            logger.exception(f"Error exporting quotes: {str(e)}")
            return JsonResponse(
                {'error': f'Export error: {str(e)}'},
                status=500
            )