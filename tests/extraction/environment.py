"""
Behave environment configuration for Django integration.
"""
import os
import sys
import django
from django.test.utils import setup_test_environment
from django.db import connection


def before_all(context):
    """Setup Django before all tests"""
    # Add project root to path
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    sys.path.insert(0, project_root)
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    setup_test_environment()
    
    # Create tables
    from django.core.management import call_command
    call_command('migrate', '--run-syncdb', verbosity=0)


def before_scenario(context, scenario):
    """Clean database before each scenario"""
    from apps.extraction.taxonomy.models import Tag
    from apps.extraction.core.models import PaperExtraction, Quote
    
    # Clear all test data
    Quote.objects.all().delete()
    PaperExtraction.objects.all().delete()
    Tag.objects.all().delete()
    
    # Initialize context storage
    context.project_id = 1  # Default project
    context.users = {}  # Store user mappings
    context.tags = {}  # Store created tags
    context.extractions = {}  # Store extractions
    context.quotes = {}  # Store quotes
    context.last_result = None
    context.last_error = None


def after_scenario(context, scenario):
    """Cleanup after each scenario"""
    pass
