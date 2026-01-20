from django.urls import path

from . import views

urlpatterns = [
    # ============================================
    # SCREENING PHASE
    # ============================================

    # Screening Overview (distribution by abstract word count)
    path('', views.screening_overview, name='screening_overview'),
    path('', views.screening_overview, name='overview'),  # Alias for backward compatibility
    path('screening/distribute/', views.distribute_screening_papers, name='distribute_screening'),
    path('screening/bulk-decision/', views.screening_bulk_decision, name='screening_bulk_decision'),
    path('screening/send-reminder/', views.send_screening_reminder, name='send_screening_reminder'),
    path('screening/finalize/', views.finalize_screening, name='finalize_screening'),

    # ============================================
    # FULLTEXT PHASE
    # ============================================

    # Fulltext Overview (PDF management + distribution by page count)
    path('fulltext/', views.fulltext_overview, name='fulltext_overview'),
    path('fulltext/distribute/', views.distribute_fulltext_papers, name='distribute_fulltext'),
    path('fulltext/download-pdfs/', views.download_overview_pdfs, name='download_pdfs'),
    path('fulltext/upload/', views.upload_overview_pdf, name='upload_pdf'),
    path('fulltext/send-reminder/', views.send_fulltext_reminder, name='send_fulltext_reminder'),
    path('fulltext/bulk-decision/', views.fulltext_bulk_decision, name='fulltext_bulk_decision'),
    path('fulltext/finalize/', views.finalize_fulltext, name='finalize_fulltext'),

    # ============================================
    # API FOR EXTRACTION MODULE
    # ============================================
    path('api/approved-papers/', views.approved_papers_api, name='approved_papers_api'),

    # ============================================
    # LEGACY COMPATIBILITY (redirect to new URLs)
    # ============================================
    path('overview/', views.screening_overview, name='overview'),  # Legacy
]
