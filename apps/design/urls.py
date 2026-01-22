from django.urls import path, include
from django.views.generic import RedirectView

from apps.design.eligibility_criteria.views import eligibility_criterion
from apps.design.research_question.views import research_question, question_discussion
from apps.design.search_strategy.views import project_keyword, search_strategy
from apps.design.design_phase_logic.views import navigation
from apps.design.shared.views import dashboard
from apps.design.design_phase_logic.views import schedule_management as design_phase_views

app_name = 'design'

# Research Questions URL patterns
question_patterns = [
    path('', research_question.open_questions_workspace_view, name='workspace'),
    path('create/', research_question.create_research_question, name='create'),
    path('autosave/', research_question.autosave_research_question, name='autosave'),
    path('<int:question_id>/', research_question.edit_research_question, name='edit'),
    path('<int:question_id>/delete/', research_question.delete_research_question, name='delete'),
    path('<int:question_id>/submit/', research_question.send_research_question_for_review, name='submit'),
    path('<int:question_id>/generate-strategy/', search_strategy.generate_and_save_search_string_for_question, name='generate_strategy'),
    path('consolidate/', research_question.consolidate_creation_stage_view, name='consolidate_creation'),
    path('schedule/manage/', design_phase_views.manage_schedule_view, name='manage_schedule'),
]

# Discussion Stage URL patterns
discussion_patterns = [
    path('', question_discussion.question_discussion_panel_view, name='panel'),
    path('review/', question_discussion.review_research_question_action, name='review'),
    path('consolidate/', question_discussion.consolidate_discussion_stage_action, name='consolidate'),
]

# Eligibility Criteria URL patterns
criteria_patterns = [
    path('', eligibility_criterion.open_eligibility_criteria_panel, name='panel'),
    path('create/', eligibility_criterion.create_eligibility_criterion, name='create'),
    path('<int:criterion_id>/', eligibility_criterion.update_eligibility_criterion, name='update'),
    path('<int:criterion_id>/approve/', eligibility_criterion.approve_eligibility_criterion, name='approve'),
    path('<int:criterion_id>/reject/', eligibility_criterion.reject_eligibility_criterion, name='reject'),
    path('<int:criterion_id>/delete/', eligibility_criterion.delete_eligibility_criterion, name='delete'),
    path('consolidate/', eligibility_criterion.consolidate_eligibility_stage, name='consolidate'),
]

# Project Keywords URL patterns
keyword_patterns = [
    path('create/', project_keyword.create_project_keyword, name='create'),
    path('<int:keyword_id>/', project_keyword.update_project_keyword, name='update'),
    path('<int:keyword_id>/delete/', project_keyword.delete_project_keyword, name='delete'),
]

# Search Strategy URL patterns
strategy_patterns = [
    path('', search_strategy.open_search_strategy_panel, name='panel'),
    path('builder/', search_strategy.search_strategy_builder_view, name='builder'),
    path('preview/', search_strategy.preview_search_string, name='preview'),
    path('translate/', search_strategy.get_translated_queries_view, name='translate'),
    path('<int:strategy_id>/save/', search_strategy.save_visual_strategy, name='save'),
    path('<int:strategy_id>/results/', search_strategy.search_results_view, name='results'),
    path('<int:strategy_id>/approve/', search_strategy.approve_strategy, name='approve'),
    path('<int:strategy_id>/reject/', search_strategy.reject_strategy, name='reject'),
    path('versions/<int:question_id>/', search_strategy.get_strategy_versions, name='versions'),
    path('version/<int:version_id>/delete/', search_strategy.delete_strategy_version, name='delete_version'),
    path('consolidate/', search_strategy.consolidate_search_strategy_stage_view, name='consolidate'),
]

urlpatterns = [
    # Root paths
    path('', navigation.design_stages_router, name='design_stages'),
    path('dashboard/', dashboard.dashboard_view, name='dashboard'),

    # Grouped resource paths with namespaces
    path('questions/', include((question_patterns, 'questions'))),
    path('discussion/', include((discussion_patterns, 'discussion'))),
    path('criteria/', include((criteria_patterns, 'criteria'))),
    path('keywords/', include((keyword_patterns, 'keywords'))),
    path('strategies/', include((strategy_patterns, 'strategies'))),

    # Backward compatibility redirects (OLD paths → NEW paths)
    path('research-questions/', RedirectView.as_view(pattern_name='design:questions:workspace', permanent=False)),
    path('eligibility-criteria/', RedirectView.as_view(pattern_name='design:criteria:panel', permanent=False)),
    path('search-strategy/', RedirectView.as_view(pattern_name='design:strategies:panel', permanent=False)),
]
