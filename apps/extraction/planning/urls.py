"""
URLs - Planning Bounded Context
Incluye tags como recursos anidados de phases.
"""
from django.urls import path, include
from . import views

urlpatterns = [
    # Phase detail (dashboard)
    path('<int:pk>/', 
         views.ExtractionPhaseDetailView.as_view(), 
         name='phase_detail'),
    
    # Phase config update
    path('<int:pk>/config/', 
         views.PhaseConfigUpdateView.as_view(), 
         name='phase_config_update'),
    
    # Phase open
    path('<int:pk>/open/', 
         views.PhaseOpenView.as_view(), 
         name='phase_open'),
    
    # Tags
    path('<int:phase_id>/tags/', 
         include(('apps.extraction.taxonomy.urls', 'taxonomy'))),
]