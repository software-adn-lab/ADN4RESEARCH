from django.urls import path

from . import views

urlpatterns = [
    path('fulltext/', views.fulltext_overview, name='fulltext_overview'),
    path('fulltext/distribute/', views.distribute_fulltext_papers, name='distribute_fulltext'),
    path('fulltext/download-pdfs/', views.download_overview_pdfs, name='download_pdfs'),
    path('fulltext/upload/', views.upload_overview_pdf, name='upload_pdf'),
    path('fulltext/send-reminder/', views.send_fulltext_reminder, name='send_fulltext_reminder'),
    path('fulltext/bulk-decision/', views.fulltext_bulk_decision, name='fulltext_bulk_decision'),
    path('fulltext/finalize/', views.finalize_fulltext, name='finalize_fulltext'),
]
