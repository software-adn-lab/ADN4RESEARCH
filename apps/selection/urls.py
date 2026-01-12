from django.urls import path
from . import views

app_name = 'selection'

urlpatterns = [
    # Overview
    path('', views.selection_overview, name='overview'),
    path('distribute/', views.distribute_papers, name='distribute'),
    
    # Screening
    path('screening/', views.screening_view, name='screening'),
    path('assignment/<int:assignment_id>/review/', views.submit_review, name='submit_review'),
    
    # Full-text
    path('fulltext/', views.fulltext_view, name='fulltext'),
    
    # Discussion
    path('discussion/', views.discussion_view, name='discussion'),
]

