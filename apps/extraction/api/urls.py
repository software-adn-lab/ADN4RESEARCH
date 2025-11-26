# apps/extraction/api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ExtractionViewSet,
    QuoteViewSet,
    TagViewSet,
    ExtractionPhaseViewSet,  # 1. Importar falta
    pdf_viewer  # 2. Importar falta
)

router = DefaultRouter()
router.register(r'phases', ExtractionPhaseViewSet, basename='phase')
router.register(r'extractions', ExtractionViewSet, basename='extraction')
router.register(r'quotes', QuoteViewSet, basename='quote')
router.register(r'tags', TagViewSet, basename='tag')

urlpatterns = [
    # Usamos cadena vacía '' para que no quede /api/extraction/extraction/...
    path('', include(router.urls)),

    # 4. Ruta específica para el viewer (fuera del router)
    path('viewer/<int:extraction_id>/', pdf_viewer, name='pdf_viewer'),
]