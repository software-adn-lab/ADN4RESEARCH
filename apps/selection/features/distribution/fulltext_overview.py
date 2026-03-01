"""Backward-compatible fulltext distribution view exports."""

from apps.selection.features.distribution.fulltext.views import (
    _count_pdf_pages,
    _calculate_fulltext_progress,
    _get_fulltext_team_progress,
    _get_pending_all_fulltext_paper_ids,
    _get_included_papers_from_screening,
    fulltext_overview,
    distribute_fulltext_papers,
    download_overview_pdfs,
    upload_overview_pdf,
    send_fulltext_reminder,
    fulltext_bulk_decision,
    finalize_fulltext,
)

__all__ = [
    '_count_pdf_pages',
    '_calculate_fulltext_progress',
    '_get_fulltext_team_progress',
    '_get_pending_all_fulltext_paper_ids',
    '_get_included_papers_from_screening',
    'fulltext_overview',
    'distribute_fulltext_papers',
    'download_overview_pdfs',
    'upload_overview_pdf',
    'send_fulltext_reminder',
    'fulltext_bulk_decision',
    'finalize_fulltext',
]
