from django.urls import path
from apps.selection.distribution import views as distribution_views
from apps.selection.screening.metadata import views as metadata_views
from apps.selection.screening.fulltext import views as fulltext_views
from apps.selection.fulltext_overview import views as fulltext_overview_views
from apps.selection.discussion import views as discussion_views

app_name = 'selection'

urlpatterns = [
    # Overview & Distribution
    path('', distribution_views.overview, name='overview'),
    path('distribute/', distribution_views.distribute_papers, name='distribute'),
    path('bulk-decision/', distribution_views.bulk_decision, name='bulk_decision'),
    path('send-reminder/', distribution_views.send_reminder, name='send_reminder'),
    
    # Screening - Metadata
    path('screening/', metadata_views.screening_view, name='screening'),
    path('assignment/<int:assignment_id>/review/', metadata_views.submit_review, name='submit_review'),
    
    # Full-text Overview
    path('fulltext-overview/', fulltext_overview_views.fulltext_overview, name='fulltext_overview'),
    path('fulltext-overview/download/', fulltext_overview_views.download_overview_pdfs, name='overview_download'),
    path('fulltext-overview/upload/', fulltext_overview_views.upload_overview_pdf, name='overview_upload'),
    
    # Screening - Full-text
    path('fulltext/', fulltext_views.fulltext_view, name='fulltext'),
    path('fulltext/retry/', fulltext_views.retry_fulltext_downloads, name='fulltext_retry'),
    path('fulltext/upload/', fulltext_views.upload_fulltext_pdf, name='fulltext_upload'),
    
    # Discussion
    path('discussion/', discussion_views.discussion_view, name='discussion'),
]

