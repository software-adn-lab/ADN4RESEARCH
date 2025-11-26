"""Compatibility shim for theme discovery views.

Re-exports implementation from `ui.interpretation.theme_discovery_views` so
existing imports continue to work while the UI container hosts the actual
presentation logic.
"""

from ui.interpretation.theme_discovery_views import *  # noqa: F401,F403
