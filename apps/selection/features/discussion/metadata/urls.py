from django.urls import path

from . import views

urlpatterns = [
    path('screening/discussion/', views.screening_discussion_view, name='screening_discussion'),
    path('screening/discussion/assign-third-reviewer/', views.assign_third_reviewer, name='assign_screening_third_reviewer'),
    path('screening/discussion/remind-third-reviewer/', views.send_screening_third_reviewer_reminder, name='screening_remind_third_reviewer'),
    path('screening/discussion/cancel-third-reviewer/', views.cancel_screening_third_reviewer_assignment, name='screening_cancel_third_reviewer'),
    path('screening/discussion/owner-vote/', views.owner_vote, name='screening_owner_vote'),
    path('screening/discussion/third-reviewer-submit/', views.third_reviewer_submit, name='screening_third_reviewer_submit'),
]
