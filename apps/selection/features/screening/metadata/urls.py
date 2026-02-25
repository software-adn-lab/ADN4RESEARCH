from django.urls import path

from . import views

urlpatterns = [
    path('screening/', views.screening_view, name='screening'),
    path('screening/assignment/<int:assignment_id>/review/', views.submit_review, name='submit_screening_review'),
]
