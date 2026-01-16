"""
Adaptation Layer - External Service Integration

Centralizes communication with external modules following Hexagonal Architecture.

MODULES:
========

1. acquisition.py (AcquisitionAdapter)
   └─ get_study_pdf_url(study_id) → Get PDF URL for Extraction UI

2. selection.py (SelectionAdapter)
   ├─ get_approved_papers(project_id)
   └─ is_selection_complete(project_id)

3. project.py (ProjectAdapter)
   └─ Various project-related operations

USAGE IN EXTRACTION VIEWS:
==========================

# Get PDF URL to display in template
from apps.extraction.adapters.acquisition import get_acquisition_adapter

adapter = get_acquisition_adapter()
pdf_url = adapter.get_study_pdf_url(study_id)

# In view context:
context['pdf_url'] = pdf_url
context['has_pdf'] = pdf_url is not None

# In template:
{% if has_pdf %}
    <canvas id="pdf-canvas" data-pdf="{{ pdf_url }}"></canvas>
{% endif %}

KEY ARCHITECTURE:
=================
✅ PDF access uses default_storage (FileSystem/S3 compatible)
✅ Centralized in adapter for easy maintenance
✅ Selection phase already handles PDF downloads
✅ Extraction phase only displays existing PDFs
"""

