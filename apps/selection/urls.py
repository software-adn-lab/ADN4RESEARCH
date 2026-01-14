from django.urls import path
from apps.selection.distribution import views as distribution_views
from apps.selection.screening.metadata import views as metadata_views
from apps.selection.screening.fulltext import views as fulltext_views
from apps.selection.fulltext_overview import views as fulltext_overview_views
from apps.selection.discussion import views as discussion_views

app_name = 'selection'

urlpatterns = [
    # ============================================
    # SCREENING PHASE
    # ============================================
    
    # Screening Overview (distribution by abstract word count)
    path('', distribution_views.screening_overview, name='screening_overview'),
    path('', distribution_views.screening_overview, name='overview'),  # Alias for backward compatibility
    path('screening/distribute/', distribution_views.distribute_screening_papers, name='distribute_screening'),
    path('screening/bulk-decision/', distribution_views.screening_bulk_decision, name='screening_bulk_decision'),
    path('screening/send-reminder/', distribution_views.send_screening_reminder, name='send_screening_reminder'),
    path('screening/finalize/', distribution_views.finalize_screening, name='finalize_screening'),
    
    # Screening (metadata review)
    path('screening/', metadata_views.screening_view, name='screening'),
    path('screening/assignment/<int:assignment_id>/review/', metadata_views.submit_review, name='submit_screening_review'),
    
    # Screening Discussion (discrepancy resolution)
    path('screening/discussion/', discussion_views.screening_discussion_view, name='screening_discussion'),
    path('screening/discussion/assign-third-reviewer/', discussion_views.assign_third_reviewer, name='assign_screening_third_reviewer'),
    path('screening/discussion/owner-vote/', discussion_views.owner_vote, name='screening_owner_vote'),
    path('screening/discussion/third-reviewer-submit/', discussion_views.third_reviewer_submit, name='screening_third_reviewer_submit'),
    
    # ============================================
    # FULLTEXT PHASE
    # ============================================
    
    # Fulltext Overview (PDF management + distribution by page count)
    path('fulltext/', fulltext_overview_views.fulltext_overview, name='fulltext_overview'),
    path('fulltext/distribute/', fulltext_overview_views.distribute_fulltext_papers, name='distribute_fulltext'),
    path('fulltext/download-pdfs/', fulltext_overview_views.download_overview_pdfs, name='download_pdfs'),
    path('fulltext/upload/', fulltext_overview_views.upload_overview_pdf, name='upload_pdf'),
    path('fulltext/send-reminder/', fulltext_overview_views.send_fulltext_reminder, name='send_fulltext_reminder'),
    path('fulltext/finalize/', fulltext_overview_views.finalize_fulltext, name='finalize_fulltext'),
    
    # Fulltext Review (PDF review)
    path('fulltext/review/', fulltext_views.fulltext_view, name='fulltext_review'),
    path('fulltext/review/assignment/<int:assignment_id>/submit/', fulltext_views.submit_fulltext_review, name='submit_fulltext_review'),
    path('fulltext/retry/', fulltext_views.retry_fulltext_downloads, name='fulltext_retry'),
    path('fulltext/review/upload/', fulltext_views.upload_fulltext_pdf, name='fulltext_upload'),
    
    # Fulltext Discussion (discrepancy resolution)
    path('fulltext/discussion/', discussion_views.fulltext_discussion_view, name='fulltext_discussion'),
    path('fulltext/discussion/assign-third-reviewer/', discussion_views.assign_fulltext_third_reviewer, name='assign_fulltext_third_reviewer'),
    path('fulltext/discussion/owner-vote/', discussion_views.fulltext_owner_vote, name='fulltext_owner_vote'),
    path('fulltext/discussion/third-reviewer-submit/', discussion_views.fulltext_third_reviewer_submit, name='fulltext_third_reviewer_submit'),
    
    # ============================================
    # API FOR EXTRACTION MODULE
    # ============================================
    path('api/approved-papers/', distribution_views.approved_papers_api, name='approved_papers_api'),
    
    # ============================================
    # LEGACY COMPATIBILITY (redirect to new URLs)
    # ============================================
    path('overview/', distribution_views.screening_overview, name='overview'),  # Legacy
]

