"""
Django app configuration for Acquisition module.
"""

from django.apps import AppConfig


class AcquisitionConfig(AppConfig):
    """Configuration for the Acquisition app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.acquisition"
    verbose_name = "Acquisition (Papers Management)"
