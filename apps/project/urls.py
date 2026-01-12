from django.urls import path
from apps.project.views import project_views, schedule_views, auth_views

app_name = 'project'

urlpatterns = [
    # Authentication
    path('', auth_views.login_view, name='login'),
    path('login/', auth_views.login_view, name='login_page'),
    path('login/submit/', auth_views.login_action, name='login_action'),
    path('logout/', auth_views.logout_action, name='logout'),
    path('projects/', auth_views.list_projects, name='list_projects'),
    
    # Projects
    path('create/', project_views.open_project_creation_screen, name='create_project_screen'),
    path('create/save/', project_views.save_project_action, name='save_project_action'),
    path('<int:project_id>/configure-schedule/', schedule_views.configure_schedule_view, name='configure_schedule'),
    path('<int:project_id>/save-schedule/', schedule_views.save_schedule_action, name='save_schedule_action'),
]
