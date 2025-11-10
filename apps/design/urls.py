from django.urls import path

from apps.design.views import research_question_views

app_name = 'design' 

urlpatterns = [
    path('', research_question_views.hello),
    path('create-research-question/', research_question_views.create_research_question, name='create_research_question'),  
    path('framework-fields/<int:framework_id>/', research_question_views.get_framework_fields),
    path('autosave-question/', research_question_views.autosave_research_question, name='autosave_research_question'),
    path('questions-history/', research_question_views.questions_history_view, name='questions_history'),
    path('edit-research-question/<int:question_id>/', research_question_views.edit_research_question, name='edit_research_question'),
    path('delete-research-question/<int:question_id>/', research_question_views.delete_research_question, name='delete_research_question'),
    path('send-research-question/<int:question_id>/', research_question_views.send_research_question_for_review, name='send_research_question_for_review'),
]