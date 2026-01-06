from django.urls import path

from apps.design.eligibility_criteria.views import eligibility_criterion
from apps.design.research_question.views import research_question, question_discussion
from apps.design.search_strategy.views import project_keyword, search_strategy
from apps.design.design_phase_logic.views import navigation
from apps.design.shared.views import dashboard

app_name = 'design'

urlpatterns = [
    # Stage Navigation Router
    path('', navigation.design_stages_router, name='design_stages'),
    path('dashboard/', dashboard.dashboard_view, name='dashboard'),

    # Research Questions
    path('research-questions/', research_question.open_questions_workspace_view, name='rq_workspace'),
    path('research-questions/create/', research_question.create_research_question, name='create_research_question'),
    path('research-questions/autosave/', research_question.autosave_research_question, name='autosave_research_question'),
    path('research-questions/<int:question_id>/', research_question.edit_research_question, name='edit_research_question'),
    path('research-questions/<int:question_id>/delete/', research_question.delete_research_question, name='delete_research_question'),
    path('research-questions/<int:question_id>/submit/', research_question.send_research_question_for_review, name='send_research_question_for_review'),
    path('research-questions/<int:question_id>/generate-strategy/', search_strategy.generate_and_save_search_string_for_question, name='get_search_strategy_for_question'),

    # Discussion Stage
    path('discussion/', question_discussion.question_discussion_panel_view, name='question_discussion_panel'),
    path('discussion/review/', question_discussion.review_research_question_action, name='review_research_question_action'),
    path('discussion/consolidate/', question_discussion.consolidate_discussion_stage_action, name='consolidate_discussion_stage'),

    # Eligibility Criteria
    path('eligibility-criteria/', eligibility_criterion.open_eligibility_criteria_panel, name='eligibility_criteria_panel'),
    path('eligibility-criteria/create/', eligibility_criterion.create_eligibility_criterion, name='create_criterion'),
    path('eligibility-criteria/<int:criterion_id>/', eligibility_criterion.update_eligibility_criterion, name='update_criterion'),
    path('eligibility-criteria/<int:criterion_id>/approve/', eligibility_criterion.approve_eligibility_criterion, name='approve_criterion'),
    path('eligibility-criteria/<int:criterion_id>/reject/', eligibility_criterion.reject_eligibility_criterion, name='reject_criterion'),
    path('eligibility-criteria/<int:criterion_id>/delete/', eligibility_criterion.delete_eligibility_criterion, name='delete_criterion'),
    path('eligibility-criteria/consolidate/', eligibility_criterion.consolidate_eligibility_stage, name='consolidate_eligibility_stage'),

    # Project Keywords
    path('keywords/create/', project_keyword.create_project_keyword, name='create_project_keyword'),
    path('keywords/<int:keyword_id>/', project_keyword.update_project_keyword, name='update_project_keyword'),
    path('keywords/<int:keyword_id>/delete/', project_keyword.delete_project_keyword, name='delete_project_keyword'),

    # Search Strategy
    path('search-strategy/', search_strategy.open_search_strategy_panel, name='open_search_strategy_panel'),
    path('search-strategy/builder/', search_strategy.search_strategy_builder_view, name='search_strategy_builder_view'),
    path('search-strategy/preview/', search_strategy.preview_search_string, name='preview_search_string'),
    path('search-strategy/<int:strategy_id>/save/', search_strategy.save_visual_strategy, name='save_visual_strategy'),
    path('search-strategy/<int:strategy_id>/results/', search_strategy.search_results_view, name='search_results_view'),
    path('search-strategy/<int:strategy_id>/approve/', search_strategy.approve_strategy, name='approve_strategy'),
    path('search-strategy/<int:strategy_id>/reject/', search_strategy.reject_strategy, name='reject_strategy'),
    path('search-strategy/versions/<int:question_id>/', search_strategy.get_strategy_versions, name='get_strategy_versions'),
    path('search-strategy/version/<int:version_id>/delete/', search_strategy.delete_strategy_version, name='delete_strategy_version'),
    path('search-strategy/consolidate/', search_strategy.consolidate_search_strategy_stage_view, name='consolidate_search_strategy_stage'),
]
