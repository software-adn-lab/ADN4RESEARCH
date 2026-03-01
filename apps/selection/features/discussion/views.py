"""Backward-compatible view exports for discussion feature."""

from apps.selection.features.discussion.metadata.views import (
    _get_paper_metadata,
    _get_criteria,
    screening_discussion_view,
    assign_third_reviewer,
    send_screening_third_reviewer_reminder,
    cancel_screening_third_reviewer_assignment,
    owner_vote,
    third_reviewer_submit,
)
from apps.selection.features.discussion.fulltext.views import (
    fulltext_discussion_view,
    assign_fulltext_third_reviewer,
    send_fulltext_third_reviewer_reminder,
    cancel_fulltext_third_reviewer_assignment,
    fulltext_owner_vote,
    fulltext_third_reviewer_submit,
)

__all__ = [
    '_get_paper_metadata',
    '_get_criteria',
    'screening_discussion_view',
    'assign_third_reviewer',
    'send_screening_third_reviewer_reminder',
    'cancel_screening_third_reviewer_assignment',
    'owner_vote',
    'third_reviewer_submit',
    'fulltext_discussion_view',
    'assign_fulltext_third_reviewer',
    'send_fulltext_third_reviewer_reminder',
    'cancel_fulltext_third_reviewer_assignment',
    'fulltext_owner_vote',
    'fulltext_third_reviewer_submit',
]
