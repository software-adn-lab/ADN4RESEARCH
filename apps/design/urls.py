from django.urls import path

from apps.design.eligibility_criteria.views import eligibility_criterion
from apps.design.research_question.views import research_question

app_name = 'design' 

urlpatterns = [
    path('', research_question.hello),
    path('create-research-question/<int:project_id>', research_question.create_research_question, name='create_research_question'),  
    path('framework-fields/<int:framework_id>/', research_question.get_framework_fields),
    path('autosave-question/', research_question.autosave_research_question, name='autosave_research_question'),
    path('questions-history/<int:project_id>', research_question.questions_history_view, name='questions_history'),
    path('edit-research-question/<int:question_id>/', research_question.edit_research_question, name='edit_research_question'),
    path('delete-research-question/<int:question_id>/', research_question.delete_research_question, name='delete_research_question'),
    path('send-research-question/<int:question_id>/', research_question.send_research_question_for_review, name='send_research_question_for_review'),
    path('eligibility-criteria-panel/<int:project_id>/', eligibility_criterion.open_eligibility_criteria_panel, name='eligibility_criteria_panel'),
]