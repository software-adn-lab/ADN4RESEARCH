from django.urls import path
from apps.selection.distribution import views as distribution_views
from apps.selection.screening.metadata import views as metadata_views
from apps.selection.screening.fulltext import views as fulltext_views
from apps.selection.discussion import views as discussion_views

app_name = 'selection'

urlpatterns = [
    # Overview & Distribution
    path('', distribution_views.overview, name='overview'),
    path('distribute/', distribution_views.distribute_papers, name='distribute'),
    
    # Screening - Metadata
    path('screening/', metadata_views.screening_view, name='screening'),
    path('assignment/<int:assignment_id>/review/', metadata_views.submit_review, name='submit_review'),
    
    # Screening - Full-text
    path('fulltext/', fulltext_views.fulltext_view, name='fulltext'),
    path('fulltext/retry/', fulltext_views.retry_fulltext_downloads, name='fulltext_retry'),
    path('fulltext/upload/', fulltext_views.upload_fulltext_pdf, name='fulltext_upload'),
    
    # Discussion
    path('discussion/', discussion_views.discussion_view, name='discussion'),
]

