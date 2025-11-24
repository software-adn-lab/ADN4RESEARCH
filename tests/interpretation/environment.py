"""Environment setup for interpretation BDD tests."""
import os
import django

# Setup Django before importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from faker import Faker
from django.contrib.auth.models import User

fake = Faker()


def before_scenario(context, _):
    """Set up default user for interpretation tests."""
    # Create a test researcher user
    context.researcher = User.objects.create_user(
        username=fake.user_name(),
        email=fake.email(),
        password='testpass123'
    )
