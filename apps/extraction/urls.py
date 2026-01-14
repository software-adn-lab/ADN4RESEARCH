"""
URL Configuration - Extraction App

Estructura:
- /project/<project_id>/extraction/
  - / -> router que redirige a la fase abierta o primera disponible
  - /phases/<phase_id>/ -> dashboard de la fase
  - /phases/<phase_id>/config/ -> configuración de la fase
  - /phases/<phase_id>/open/ -> abrir la fase
  - /phases/<phase_id>/tags/ -> tags de extracción
  - /papers/<paper_id>/ -> detalle del paper
  - /papers/<paper_id>/pdf/ -> PDF del paper
  - /papers/<paper_id>/complete/ -> completar paper
  - /quotes/create/ -> crear quote
  - /quotes/<quote_id>/delete/ -> eliminar quote
"""
from django.urls import path, include
from apps.extraction.design_phase_logic.views import extraction_phases_router
from apps.extraction.planning import urls as planning_urls
from apps.extraction.core import urls as core_urls

app_name = 'extraction'

urlpatterns = [
    # Root router - redirige a la fase abierta o primera
    path('', extraction_phases_router, name='router'),
    
    # Planning (Phases) - con namespace
    path('phases/', include((planning_urls.urlpatterns, 'planning'))),
    
    # Core (Papers y Quotes) - con namespace
    path('papers/', include((core_urls.urlpatterns, 'core'))),
]