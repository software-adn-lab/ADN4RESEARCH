"""
Dashboard configuration for Design Phase.

Defines the visual stages and their mappings to internal stage codes.
"""

# Define the visual stages for the dashboard (maps internal stages to UI)
DASHBOARD_STAGES = [
    {
        'id': 1,
        'key': 'research_questions',
        'title': 'Research Questions Workspace',
        'internal_stages': ['RQ_CREATION'],
        'url_name': 'design:questions:workspace',
        'artifacts': [
            {'key': 'questions', 'label': 'Research Questions'},
        ]
    },
    {
        'id': 2,
        'key': 'research_questions',
        'title': 'Research Questions Discussion',
        'internal_stages': ['RQ_DISCUSSION'],
        'url_name': 'design:discussion:panel',
        'artifacts': [
            {'key': 'questions', 'label': 'Research Questions'},
        ]
    },
    {
        'id': 3,
        'key': 'eligibility',
        'title': 'Eligibility Criteria',
        'internal_stages': ['CRITERIA_DEFINITION'],
        'url_name': 'design:criteria:panel',
        'artifacts': [
            {'key': 'inclusion_criteria', 'label': 'Inclusion Criteria'},
            {'key': 'exclusion_criteria', 'label': 'Exclusion Criteria'},
        ]
    },
    {
        'id': 4,
        'key': 'search_strategy',
        'title': 'Search Strategy Development',
        'internal_stages': ['SEARCH_STRATEGY'],
        'url_name': 'design:strategies:panel',
        'artifacts': [
            {'key': 'search_strategies', 'label': 'Search Strategies'},
        ]
    },
]
