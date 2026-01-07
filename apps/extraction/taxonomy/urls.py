"""
URLs - Taxonomy Bounded Context
Gestión de etiquetas (tags) deductivos e inductivos.

Estas URLs están anidadas bajo /extraction/phases/<phase_id>/tags/

Referencia Django URLs:
https://docs.djangoproject.com/en/stable/topics/http/urls/
"""
from django.urls import path
from . import views

# ⚠️ IMPORTANTE: NO usar app_name aquí si está definido en el padre
# El namespace se hereda del URLconf padre

urlpatterns = [
    # ==========================================================================
    # CREACIÓN DE TAGS
    # ==========================================================================
    
    # POST /extraction/phases/<phase_id>/tags/create/
    # Crear tag deductivo (requiere ser owner del proyecto)
    path(
        'create/',
        views.TagCreateView.as_view(),
        name='tag_create'
    ),
    
    # GET/POST /extraction/phases/<phase_id>/tags/create-inductive/
    # Crear tag inductivo durante extracción
    path(
        'create-inductive/',
        views.InductiveTagCreateView.as_view(),
        name='inductive_tag_create'
    ),
    
    # ==========================================================================
    # LISTADO Y CONSULTA
    # ==========================================================================
    
    # GET /extraction/phases/<phase_id>/tags/
    # Listar todos los tags de la fase con filtros
    path(
        '',
        views.TagListView.as_view(),
        name='tag_list'
    ),
    
    # GET /extraction/phases/<phase_id>/tags/pending/
    # Listar tags inductivos pendientes de aprobación (solo owner)
    path(
        'pending/',
        views.PendingTagsListView.as_view(),
        name='pending_tags'
    ),
    
    # GET /extraction/phases/<phase_id>/tags/api/usable/
    # API JSON para obtener tags usables por el usuario actual
    path(
        'api/usable/',
        views.UsableTagsAPIView.as_view(),
        name='usable_tags_api'
    ),
    
    # ==========================================================================
    # APROBACIÓN Y RECHAZO
    # ==========================================================================
    
    # POST /extraction/phases/<phase_id>/tags/<pk>/approve/
    # Aprobar un tag inductivo (solo owner)
    path(
        '<int:pk>/approve/',
        views.TagApproveView.as_view(),
        name='tag_approve'
    ),
    
    # POST /extraction/phases/<phase_id>/tags/<pk>/reject/
    # Rechazar un tag inductivo (solo owner)
    path(
        '<int:pk>/reject/',
        views.TagRejectView.as_view(),
        name='tag_reject'
    ),
    
    # POST /extraction/phases/<phase_id>/tags/bulk-approve/
    # Aprobar múltiples tags inductivos (solo owner)
    path(
        'bulk-approve/',
        views.BulkTagApproveView.as_view(),
        name='tags_bulk_approve'
    ),
]