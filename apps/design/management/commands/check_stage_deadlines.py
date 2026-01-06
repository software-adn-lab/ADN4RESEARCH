from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.design.design_phase_logic.services.design_phase_service import DesignPhaseService

class Command(BaseCommand):
    help = 'Checks for expired RQ_CREATION stages and consolidates them automatically.'

    def handle(self, *args, **options):
        self.stdout.write("Checking for expired RQ_CREATION stages...")

        User = get_user_model()
        system_user = User.objects.filter(is_superuser=True).first()

        if not system_user:
            self.stdout.write(self.style.WARNING("No superuser found for system actions. Skipping."))
            return

        service = DesignPhaseService()
        count = service.check_deadlines_and_consolidate(system_user)

        self.stdout.write(self.style.SUCCESS(f"Successfully consolidated {count} stages."))
