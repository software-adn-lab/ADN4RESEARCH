from django.urls import path

from . import views

urlpatterns = [
    path('fulltext/discussion/', views.fulltext_discussion_view, name='fulltext_discussion'),
    path('fulltext/discussion/assign-third-reviewer/', views.assign_fulltext_third_reviewer, name='assign_fulltext_third_reviewer'),
    path('fulltext/discussion/owner-vote/', views.fulltext_owner_vote, name='fulltext_owner_vote'),
    path('fulltext/discussion/third-reviewer-submit/', views.fulltext_third_reviewer_submit, name='fulltext_third_reviewer_submit'),
]
