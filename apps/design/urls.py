from django.urls import path

from apps.design.eligibility_criteria.views import eligibility_criterion
from apps.design.research_question.views import research_question
from apps.design.search_strategy.views import project_keyword

app_name = 'design' 

urlpatterns = [
    path('', research_question.hello),
    path('create-research-question/<int:project_id>', research_question.create_research_question, name='create_research_question'),  
    path('framework-fields/<int:framework_id>/', research_question.get_framework_fields),
    path('autosave-question/', research_question.autosave_research_question, name='autosave_research_question'),
    path('rq-workspace/<int:project_id>', research_question.open_questions_workspace_view, name='questions_history'),
    path('edit-research-question/<int:question_id>/', research_question.edit_research_question, name='edit_research_question'),
    path('delete-research-question/<int:question_id>/', research_question.delete_research_question, name='delete_research_question'),
    path('send-research-question/<int:question_id>/', research_question.send_research_question_for_review, name='send_research_question_for_review'),
    path('eligibility-criteria-panel/<int:project_id>/', eligibility_criterion.open_eligibility_criteria_panel, name='eligibility_criteria_panel'),
    path('create-criterion/<int:project_id>/', eligibility_criterion.create_eligibility_criterion, name='create_criterion'),
    path('update-criterion/<int:criterion_id>/', eligibility_criterion.update_eligibility_criterion, name='update_criterion'),
    path('approve-criterion/<int:criterion_id>/', eligibility_criterion.approve_eligibility_criterion, name='approve_criterion'),
    path('reject-criterion/<int:criterion_id>/', eligibility_criterion.reject_eligibility_criterion, name='reject_criterion'),
    path('delete-criterion/<int:criterion_id>/', eligibility_criterion.delete_eligibility_criterion, name='delete_criterion'),
    
    path('project-keyword/create/<int:project_id>/', project_keyword.create_project_keyword, name='create_project_keyword'),
    path('project-keyword/update/<int:keyword_id>/', project_keyword.update_project_keyword, name='update_project_keyword'),
    path('project-keyword/delete/<int:keyword_id>/', project_keyword.delete_project_keyword, name='delete_project_keyword'),
    
    
]