"""Compatibility shims for interpretation views.

These shims re-export the presentation-level view functions from the
`ui.interpretation` package so existing imports (e.g. in `urls.py`) keep
working while the UI layer is separated into the `ui/` container.
"""

from ui.interpretation.views import *  # noqa: F401,F403
