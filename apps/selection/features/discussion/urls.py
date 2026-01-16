from django.urls import path

from . import views

urlpatterns = [
    # Screening Discussion (discrepancy resolution)
    path('screening/discussion/', views.screening_discussion_view, name='screening_discussion'),
    path('screening/discussion/assign-third-reviewer/', views.assign_third_reviewer, name='assign_screening_third_reviewer'),
    path('screening/discussion/owner-vote/', views.owner_vote, name='screening_owner_vote'),
    path('screening/discussion/third-reviewer-submit/', views.third_reviewer_submit, name='screening_third_reviewer_submit'),

    # Fulltext Discussion (discrepancy resolution)
    path('fulltext/discussion/', views.fulltext_discussion_view, name='fulltext_discussion'),
    path('fulltext/discussion/assign-third-reviewer/', views.assign_fulltext_third_reviewer, name='assign_fulltext_third_reviewer'),
    path('fulltext/discussion/owner-vote/', views.fulltext_owner_vote, name='fulltext_owner_vote'),
    path('fulltext/discussion/third-reviewer-submit/', views.fulltext_third_reviewer_submit, name='fulltext_third_reviewer_submit'),
]
