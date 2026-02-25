from django.urls import path

from . import views

urlpatterns = [
    path('', views.screening_overview, name='screening_overview'),
    path('', views.screening_overview, name='overview'),
    path('overview/', views.screening_overview, name='overview_legacy'),
    path('schedule/', views.configure_selection_schedule, name='configure_selection_schedule'),
    path('screening/distribute/', views.distribute_screening_papers, name='distribute_screening'),
    path('screening/bulk-decision/', views.screening_bulk_decision, name='screening_bulk_decision'),
    path('screening/send-reminder/', views.send_screening_reminder, name='send_screening_reminder'),
    path('screening/finalize/', views.finalize_screening, name='finalize_screening'),
    path('api/approved-papers/', views.approved_papers_api, name='approved_papers_api'),
]
