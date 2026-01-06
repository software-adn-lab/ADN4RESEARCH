from django import template

register = template.Library()


@register.inclusion_tag('design/partials/status_filter.html')
def render_status_filter(current_filter=None):
    """
    Renders a status filter dropdown for the Research Question workspace.

    Args:
        current_filter: The currently selected status filter value

    Returns:
        Context dict with status options and current filter
    """
    statuses = [
        {'value': '', 'label': 'All Statuses'},
        {'value': 'DRAFT', 'label': 'Draft'},
        {'value': 'READY_TO_SEND', 'label': 'Ready to send'},
        {'value': 'SUGGESTED', 'label': 'Suggested'},
    ]
    return {'statuses': statuses, 'current_filter': current_filter}
