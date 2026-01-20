from django.urls import path

from . import views

urlpatterns = [
    # Screening (metadata review)
    path('screening/', views.screening_view, name='screening'),
    path('screening/assignment/<int:assignment_id>/review/', views.submit_review, name='submit_screening_review'),

    # Fulltext Review (PDF review)
    path('fulltext/review/', views.fulltext_view, name='fulltext_review'),
    path('fulltext/review/assignment/<int:assignment_id>/submit/', views.submit_fulltext_review, name='submit_fulltext_review'),
    path('fulltext/retry/', views.retry_fulltext_downloads, name='fulltext_retry'),
    path('fulltext/review/upload/', views.upload_fulltext_pdf, name='fulltext_upload'),
]
