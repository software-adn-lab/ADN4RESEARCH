from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Accede a un item de un diccionario por clave.
    
    Uso en template: {{ my_dict|get_item:"key_name" }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.inclusion_tag('partials/status_filter.html')
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
