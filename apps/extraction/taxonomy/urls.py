"""
URLs del Bounded Context: Taxonomy (Tags)
"""
from django.urls import path
from .views import (
    CreateTagView,
    # Futuros:
    # TagListView,
    # TagUpdateView,
    # TagDeleteView,
)

urlpatterns = [
    path('<int:phase_id>/create/', 
         CreateTagView.as_view(), 
         name='create_tag'),
    
    # path('', TagListView.as_view(), name='tag_list'),
    # path('<int:pk>/edit/', TagUpdateView.as_view(), name='tag_update'),
]