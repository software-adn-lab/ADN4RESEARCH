from django.urls import path

from apps.design.views import views

app_name = 'design' 

urlpatterns = [
    path('', views.hello),
    path('create-research-question/', views.create_research_question, name='create_research_question'),  
    path('framework-fields/<int:framework_id>/', views.get_framework_fields),
    path('autosave-question/', views.autosave_research_question, name='autosave_research_question'),
    path('questions-history/', views.load_questions_history, name='questions_history'),
    path('edit-research-question/<int:question_id>/', views.edit_research_question, name='edit_research_question'),
    path('delete-research-question/<int:question_id>/', views.delete_research_question, name='delete_research_question'),
]