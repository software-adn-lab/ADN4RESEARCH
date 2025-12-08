"""Custom template tags for rendering Markdown content."""

import markdown as md
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="markdown")
def markdown_filter(text):
    """
    Convert Markdown text to HTML.

    Usage in templates:
        {{ text|markdown }}

    Supports:
    - Headers (# ## ###)
    - Bold (**text** or __text__)
    - Italic (*text* or _text_)
    - Code blocks (```code```)
    - Inline code (`code`)
    - Lists (ordered and unordered)
    - Links [text](url)
    - Blockquotes (>)
    - Horizontal rules (---)
    """
    if not text:
        return ""

    # Configure markdown extensions for better formatting
    extensions = [
        "markdown.extensions.fenced_code",  # ```code blocks```
        "markdown.extensions.codehilite",  # Syntax highlighting
        "markdown.extensions.tables",  # Tables support
        "markdown.extensions.nl2br",  # Convert newlines to <br>
        "markdown.extensions.sane_lists",  # Better list handling
    ]

    extension_configs = {
        "markdown.extensions.codehilite": {
            "css_class": "highlight",
            "linenums": False,
        }
    }

    # Convert markdown to HTML
    html = md.markdown(text, extensions=extensions, extension_configs=extension_configs)

    # Mark as safe HTML
    return mark_safe(html)


@register.filter(name="markdown_inline")
def markdown_inline_filter(text):
    """
    Convert Markdown text to HTML without block-level elements.
    Useful for inline text where you want basic formatting but no paragraphs.

    Usage in templates:
        {{ text|markdown_inline }}
    """
    if not text:
        return ""

    # Convert markdown
    html = md.markdown(text)

    # Remove wrapping <p> tags if present
    if html.startswith("<p>") and html.endswith("</p>"):
        html = html[3:-4]

    return mark_safe(html)
