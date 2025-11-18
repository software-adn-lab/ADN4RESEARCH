"""
Behave environment configuration for Django integration.

This file is automatically loaded by Behave before running tests and is used to
configure Django settings and set up the test environment.

Note: When using behave-django, most of the Django test setup is handled
automatically. This file is kept minimal to avoid conflicts with behave-django's
internal test management.
"""

import os
import django


def before_all(context):
    """
    Configure Django before running any tests.

    This function is called once before the entire test suite runs.
    It sets up Django's settings module and initializes the Django application.
    """
    # Set the Django settings module
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    # Initialize Django
    django.setup()

    # Note: behave-django handles setup_test_environment() automatically
