from django.urls import path

from apps.design.eligibility_criteria.views import eligibility_criterion
from apps.design.research_question.views import research_question
from apps.design.search_strategy.views import project_keyword, search_strategy
from apps.design.research_question.views import question_discussion
from apps.design.shared.views import navigation

app_name = 'design'

urlpatterns = [
    path('', research_question.hello, name='hello'),
    # Lo que se relaciona con Research Questions
    path('rq-workspace/<int:project_id>', research_question.open_questions_workspace_view, name='rq_workspace'),
    path('create-research-question/<int:project_id>', research_question.create_research_question, name='create_research_question'),
    path('autosave-question/', research_question.autosave_research_question, name='autosave_research_question'),
    path('edit-research-question/<int:question_id>/', research_question.edit_research_question, name='edit_research_question'),
    path('delete-research-question/<int:question_id>/', research_question.delete_research_question, name='delete_research_question'),
    path('send-research-question/<int:question_id>/', research_question.send_research_question_for_review, name='send_research_question_for_review'),
    path('get-strategy/question/<int:question_id>/', search_strategy.generate_and_save_search_string_for_question, name='get_search_strategy_for_question'),  # Para las automaticas se generan al momento de guardar
    # 'design:design_stages' project.id
    path('design-stages/<int:project_id>/', navigation.design_stages_router, name='design_stages'),

    path('discussion/<int:project_id>/', question_discussion.question_discussion_panel_view, name='question_discussion_panel'),
    path('discussion/review/', question_discussion.review_research_question_action, name='review_research_question_action'),
    path('discussion/consolidate/<int:project_id>/', question_discussion.consolidate_discussion_stage_action, name='consolidate_discussion_stage'),

    path('eligibility-criteria-panel/<int:project_id>/', eligibility_criterion.open_eligibility_criteria_panel, name='eligibility_criteria_panel'),
    path('create-criterion/<int:project_id>/', eligibility_criterion.create_eligibility_criterion, name='create_criterion'),
    path('update-criterion/<int:criterion_id>/', eligibility_criterion.update_eligibility_criterion, name='update_criterion'),
    path('approve-criterion/<int:criterion_id>/', eligibility_criterion.approve_eligibility_criterion, name='approve_criterion'),
    path('reject-criterion/<int:criterion_id>/', eligibility_criterion.reject_eligibility_criterion, name='reject_criterion'),
    path('delete-criterion/<int:criterion_id>/', eligibility_criterion.delete_eligibility_criterion, name='delete_criterion'),
    path('consolidate-eligibility/<int:project_id>/', eligibility_criterion.consolidate_eligibility_stage, name='consolidate_eligibility_stage'),

    path('project-keyword/create/<int:project_id>/', project_keyword.create_project_keyword, name='create_project_keyword'),
    path('project-keyword/update/<int:keyword_id>/', project_keyword.update_project_keyword, name='update_project_keyword'),
    path('project-keyword/delete/<int:keyword_id>/', project_keyword.delete_project_keyword, name='delete_project_keyword'),

    path('search-strategy/builder/<int:project_id>/',
         search_strategy.search_strategy_builder_view,
         name='search_strategy_builder_view'),
    path('search-strategy/save-visual/<int:strategy_id>/', search_strategy.save_visual_strategy, name='save_visual_strategy'),
    path('search-strategy/versions/<int:question_id>/', search_strategy.get_strategy_versions, name='get_strategy_versions'),
    path('search-strategy/panel/<int:project_id>/', search_strategy.open_search_strategy_panel, name='open_search_strategy_panel'),
    # search_strategy_builder_view
    path('search-strategy/results/<int:strategy_id>/', search_strategy.search_results_view, name='search_results_view'),
    path('search-strategy/approve/<int:strategy_id>/', search_strategy.approve_strategy, name='approve_strategy'),
    path('search-strategy/reject/<int:strategy_id>/', search_strategy.reject_strategy, name='reject_strategy'),
    path('search-strategy/version/delete/<int:version_id>/', search_strategy.delete_strategy_version, name='delete_strategy_version'),
    path('search-strategy/consolidate/<int:project_id>/', search_strategy.consolidate_search_strategy_stage_view, name='consolidate_search_strategy_stage'),
]
