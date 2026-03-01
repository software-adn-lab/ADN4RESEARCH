"""Backward-compatible view exports for discussion feature."""

from apps.selection.features.discussion.metadata.views import (
    _get_paper_metadata,
    _get_criteria,
    screening_discussion_view,
    assign_third_reviewer,
    owner_vote,
    third_reviewer_submit,
)
from apps.selection.features.discussion.fulltext.views import (
    fulltext_discussion_view,
    assign_fulltext_third_reviewer,
    fulltext_owner_vote,
    fulltext_third_reviewer_submit,
)

__all__ = [
    '_get_paper_metadata',
    '_get_criteria',
    'screening_discussion_view',
    'assign_third_reviewer',
    'owner_vote',
    'third_reviewer_submit',
    'fulltext_discussion_view',
    'assign_fulltext_third_reviewer',
    'fulltext_owner_vote',
    'fulltext_third_reviewer_submit',
]
