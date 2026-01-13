# Selection Module - Scripts

This directory contains JavaScript files for the Selection module UI.

## Structure

```
ui/selection/
├── static/
│   └── selection/
│       └── scripts/
│           ├── fulltext.js    # Full-text PDF viewer logic
│           └── screening.js   # Metadata screening logic
└── templates/
    ├── _timeline.html
    ├── discussion/
    │   └── discussion.html
    ├── distribution/
    │   └── overview.html
    └── screening/
        ├── fulltext/
        │   └── fulltext.html  # Uses fulltext.js
        └── metadata/
            └── screening.html  # Uses screening.js
```

## Files

### fulltext.js
Handles PDF viewing functionality:
- PDF.js integration for rendering
- Zoom in/out controls
- Multi-page rendering
- PDF download retry
- Manual PDF upload
- Decision modals for full-text screening

### screening.js
Handles metadata screening functionality:
- Paper navigation and selection
- Decision modals with criteria selection
- Inclusion/exclusion criteria management
- Notes and observations
- Scroll position preservation

## Usage

Templates load these scripts using Django's `{% static %}` template tag:

```html
<script src="{% static 'selection/scripts/fulltext.js' %}"></script>
```

Each script exposes initialization functions that accept template-specific data:
- `initFulltextViewer(urls)` - Receives Django URL endpoints
- `initScreeningViewer(criteriaData)` - Receives inclusion/exclusion criteria
