from django.urls import path

from . import views

urlpatterns = [
    path('fulltext/review/', views.fulltext_view, name='fulltext_review'),
    path('fulltext/review/assignment/<int:assignment_id>/submit/', views.submit_fulltext_review, name='submit_fulltext_review'),
    path('fulltext/retry/', views.retry_fulltext_downloads, name='fulltext_retry'),
    path('fulltext/review/upload/', views.upload_fulltext_pdf, name='fulltext_upload'),
]
