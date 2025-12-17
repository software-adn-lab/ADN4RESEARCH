from django.urls import path

from .core.views import PDFServeView, PaperWorkspaceView, QuoteCreateView
from .views import (
    ExtractionDashboardView,
    PhaseConfigUpdateView,
    CreateTagView,
    OpenPhaseView
)

app_name = 'extraction'

urlpatterns = [
    # Dashboard principal (Maneja los tabs con ?tab=...)
    path('<int:phase_id>/', ExtractionDashboardView.as_view(), name='dashboard'),

    # Acciones (POST only)
    path('<int:phase_id>/config/update/', PhaseConfigUpdateView.as_view(), name='update_config'),
    path('<int:phase_id>/tags/create/', CreateTagView.as_view(), name='create_tag'),
    path('<int:phase_id>/open/', OpenPhaseView.as_view(), name='open_phase'),
    path('quotes/create/', QuoteCreateView.as_view(), name='quote_create'),
    path('paper/<int:paper_id>/pdf/', PDFServeView.as_view(), name='serve_pdf'),
    path('paper/<int:pk>/workspace/', PaperWorkspaceView.as_view(), name='paper_workspace'),
]