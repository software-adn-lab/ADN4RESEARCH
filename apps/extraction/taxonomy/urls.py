"""
URLs - Taxonomy Bounded Context
Estas URLs están anidadas bajo /phases/<phase_id>/tags/
"""
from django.urls import path
from . import views

# ⚠️ IMPORTANTE: NO usar app_name aquí (ya está en el padre)
urlpatterns = [
    # POST /extraction/phases/<phase_id>/tags/create/
    path('create/', 
         views.TagCreateView.as_view(), 
         name='tag_create'),
    
    # Futuros:
    # path('<int:pk>/update/', views.TagUpdateView.as_view(), name='tag_update'),
    # path('<int:pk>/delete/', views.TagDeleteView.as_view(), name='tag_delete'),
]