"""
URL Configuration - Extraction App
"""
from django.urls import path, include

app_name = 'extraction'

urlpatterns = [
    # Planning (Phases)
    path('phases/', include('apps.extraction.planning.urls')),
    
    # Core (Papers y Quotes) - Sin cambios
    path('papers/', include('apps.extraction.core.urls')),
]