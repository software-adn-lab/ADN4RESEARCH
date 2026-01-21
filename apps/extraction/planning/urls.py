"""
URLs - Planning Bounded Context

Estructura simplificada:
- / -> dashboard de la fase (obtenida automáticamente del proyecto)
- /init/ -> inicializar fase desde selección
- /config/ -> configuración de la fase
- /open/ -> abrir la fase
- /tags/ -> tags de extracción (anidados)

La phase se obtiene automáticamente usando el project_id de la URL principal.
"""
from django.urls import path, include
from . import views

urlpatterns = [
    # Initialize extraction phase from selection
    path('init/', 
         views.InitializeExtractionPhaseView.as_view(), 
         name='initialize'),
    
    # Phase detail (dashboard) - obtenida del proyecto
    path('', 
         views.ExtractionPhaseDetailView.as_view(), 
         name='phase_detail'),
    
    # Phase config update
    path('config/', 
         views.PhaseConfigUpdateView.as_view(), 
         name='phase_config_update'),
    
    # Phase open
    path('open/', 
         views.PhaseOpenView.as_view(), 
         name='phase_open'),
    
    # Phase reopen
    path('reopen/', 
         views.PhaseReopenView.as_view(), 
         name='phase_reopen'),

    # Start Interpretation
    path('start-interpretation/',
         views.StartInterpretationView.as_view(),
         name='start_interpretation'),
    
    # Tags - anidados bajo la phase del proyecto
    path('tags/', 
         include(('apps.extraction.taxonomy.urls', 'taxonomy'))),
]