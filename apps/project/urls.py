from django.urls import path
from apps.project.views import project_views

app_name = 'project'

urlpatterns = [
    path('create/', project_views.open_project_creation_screen, name='create_project_screen'),
    path('create/save/', project_views.save_project_action, name='save_project_action'),
]
