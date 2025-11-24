"""
Django management command to set up test data for Theme Discovery feature.

Usage:
    python manage.py setup_theme_discovery_demo
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.project.models import Project
from apps.interpretation.conclusion_assistant.services.theme_discovery_services import (
    ThemeDiscoveryService,
)
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = "Creates a demo project with initial codes for testing Theme Discovery UI"

    def handle(self, *args, **options):
        
        service = ThemeDiscoveryService()

        # Create or get test user
        try:
            user = User.objects.get(username="demo_user")
            self.stdout.write(
                self.style.WARNING(f"→ Using existing user: {user.username}")
            )
        except User.DoesNotExist:
            # Create user with all required fields including last_login
            user = User(
                username="demo_user",
                email="demo@example.com",
                first_name="Demo",
                last_name="User",
                last_login=timezone.now(),
                is_active=True,
                is_staff=False,
                is_superuser=False,
            )
            user.set_password("demo123")
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f"✓ Created demo user: {user.username}")
            )

        # Create or get test project
        project, created = Project.objects.get_or_create(
            name="Theme Discovery Demo Project",
            defaults={
                "description": "Demo project for testing AI-Driven Theme Discovery feature",
                "owner": user,
            },
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f"✓ Created demo project: {project.name}")
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"→ Using existing project: {project.name}")
            )

        # Sample initial codes (tags) from a mental health systematic review
        sample_codes = [
            {"code": "Anxiety", "frequency": 45},
            {"code": "anxiety symptoms", "frequency": 23},
            {"code": "Anxiety disorders", "frequency": 18},
            {"code": "Depression", "frequency": 67},
            {"code": "depressive symptoms", "frequency": 34},
            {"code": "Major depression", "frequency": 21},
            {"code": "Cognitive Behavioral Therapy", "frequency": 52},
            {"code": "CBT", "frequency": 48},
            {"code": "Cognitive therapy", "frequency": 15},
            {"code": "Treatment efficacy", "frequency": 38},
            {"code": "Intervention effectiveness", "frequency": 29},
            {"code": "therapeutic outcomes", "frequency": 22},
            {"code": "Patient outcomes", "frequency": 41},
            {"code": "clinical outcomes", "frequency": 33},
            {"code": "Quality of life", "frequency": 56},
            {"code": "QoL", "frequency": 44},
            {"code": "Well-being", "frequency": 37},
            {"code": "Mental health", "frequency": 89},
            {"code": "psychological health", "frequency": 28},
            {"code": "Stress", "frequency": 62},
            {"code": "stress levels", "frequency": 31},
            {"code": "chronic stress", "frequency": 19},
            {"code": "Randomized controlled trial", "frequency": 71},
            {"code": "RCT", "frequency": 68},
            {"code": "Sample size", "frequency": 54},
            {"code": "study participants", "frequency": 47},
            {"code": "Medication", "frequency": 43},
            {"code": "pharmacotherapy", "frequency": 26},
            {"code": "Psychotherapy", "frequency": 49},
            {"code": "psychological intervention", "frequency": 24},
        ]

        # Load initial codes
        self.stdout.write(self.style.MIGRATE_HEADING("\n→ Loading initial codes..."))
        loaded_codes = service.load_initial_codes(sample_codes, project=project)
        self.stdout.write(
            self.style.SUCCESS(f"✓ Loaded {len(loaded_codes)} initial codes")
        )

        # Display summary
        self.stdout.write(
            self.style.SUCCESS(
                "\n" + "=" * 70 + "\n"
                "✓ Demo setup complete!\n"
                "=" * 70 + "\n"
                f"Project ID: {project.id}\n"
                f"Project Name: {project.name}\n"
                f"Initial Codes: {len(loaded_codes)}\n"
                f"\nAccess the Theme Discovery UI at:\n"
                f"http://localhost:8000/interpretation/theme-discovery/{project.id}/\n"
                "\n"
                f"Login credentials:\n"
                f"Username: demo_user\n"
                f"Password: demo123\n"
                "=" * 70
            )
        )

        # Display sample codes
        self.stdout.write(self.style.MIGRATE_HEADING("\nSample Initial Codes:"))
        for code in loaded_codes[:10]:
            self.stdout.write(f"  • {code.code} (frequency: {code.frequency})")
        if len(loaded_codes) > 10:
            self.stdout.write(f"  ... and {len(loaded_codes) - 10} more")
