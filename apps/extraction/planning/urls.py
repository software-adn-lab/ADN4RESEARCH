"""
URLs del Bounded Context: Planning (Fases de Extracción)
"""
from django.urls import path
from .views import (
    ExtractionDashboardView,
    PhaseConfigUpdateView,
    OpenPhaseView,
)

# NO necesitas app_name aquí (ya está en el padre)
urlpatterns = [
    # Dashboard principal
    path('<int:phase_id>/', 
         ExtractionDashboardView.as_view(), 
         name='dashboard'),
    
    # Acciones de fase
    path('<int:phase_id>/config/update/', 
         PhaseConfigUpdateView.as_view(), 
         name='update_config'),
    
    path('<int:phase_id>/open/', 
         OpenPhaseView.as_view(), 
         name='open_phase'),
]