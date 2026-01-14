"""
URL Configuration - Extraction App

Estructura:
- /project/<project_id>/extraction/
  - / -> dashboard de la fase (obtenida del proyecto)
  - /config/ -> configuración de la fase
  - /open/ -> abrir la fase
  - /tags/ -> tags de extracción
  - /papers/<paper_id>/ -> detalle del paper
  - /papers/<paper_id>/pdf/ -> PDF del paper
  - /papers/<paper_id>/complete/ -> completar paper
  - /quotes/create/ -> crear quote
  - /quotes/<quote_id>/delete/ -> eliminar quote
"""
from django.urls import path, include
from apps.extraction.planning import urls as planning_urls
from apps.extraction.core import urls as core_urls

app_name = 'extraction'

urlpatterns = [
    # Planning (Phases) - con namespace - obtiene phase del project_id
    path('', include((planning_urls.urlpatterns, 'planning'))),
    
    # Core (Papers y Quotes) - con namespace
    path('papers/', include((core_urls.urlpatterns, 'core'))),
]