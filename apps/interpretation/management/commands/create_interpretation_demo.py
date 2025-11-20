from django.core.management.base import BaseCommand

from django.contrib.auth import get_user_model

from apps.interpretation.conclusion_assistant.models.theme_models import Theme
from apps.interpretation.conclusion_assistant.models.subtheme_models import SubTheme
from apps.interpretation.conclusion_assistant.services.interpretation_services import InterpretationService


class Command(BaseCommand):
    help = "Create demo SubThemes for existing Themes (from theme_discovery) and start InterpretationContext. If no themes exist, creates a demo theme."

    def handle(self, *args, **options):
        svc = InterpretationService()

        # Find an existing user to set as created_by; if none exists, create a demo superuser.
        User = get_user_model()
        user = User.objects.filter(is_superuser=True).first() or User.objects.filter(is_staff=True).first() or User.objects.first()
        if not user:
            # Create a demo superuser with a simple password — instruct the developer to change it.
            user = User.objects.create_superuser(username="demo", email="demo@example.com", password="demo123")
            self.stdout.write(self.style.WARNING("No existing users found — created demo superuser 'demo' with password 'demo123'. Change this in production."))

        # Check if there are existing themes from theme_discovery
        existing_themes = Theme.objects.all()
        
        if existing_themes.exists():
            # Use the first existing theme
            theme = existing_themes.first()
            self.stdout.write(self.style.SUCCESS(f"Using existing theme: {theme.name} (id={theme.id})"))
        else:
            # Create a demo theme if none exists
            theme = Theme.objects.create(
                name="Antipatrones en el desarrollo de software",
                research_question=(
                    "¿Cuáles son los desafíos técnicos y organizacionales reportados al implementar DevOps en equipos distribuidos?"
                ),
                created_by=user,
            )
            self.stdout.write(self.style.SUCCESS(f"Created new demo Theme id={theme.id}"))

        # Create demo subtemes if they don't exist
        if not theme.subthemes.exists():
            sub = SubTheme.objects.create(
                theme=theme,
                name="Retos Culturales y de Comunicación",
                central_codes=["Comunicación asíncrona", "Zonas horarias", "Gestión de equipos distribuidos"],
                key_citations=[
                    "Author et al. (2020): 'Challenges in distributed teams show communication gaps...'",
                    "Smith et al. (2021): 'Time zone differences impact productivity by 30%...'"
                ],
            )
            self.stdout.write(self.style.SUCCESS(f"Created SubTheme id={sub.id}: {sub.name}"))
        else:
            sub = theme.subthemes.first()
            self.stdout.write(self.style.SUCCESS(f"Using existing SubTheme id={sub.id}: {sub.name}"))

        # Initiate interpretation context
        context, _ = svc.initiate_interpretation_context(sub)

        self.stdout.write(self.style.SUCCESS("\n✓ Interpretation context created successfully!"))
        self.stdout.write(self.style.SUCCESS(f"  Theme: {theme.name} (id={theme.id})"))
        self.stdout.write(self.style.SUCCESS(f"  SubTheme: {sub.name} (id={sub.id})"))
        self.stdout.write(self.style.SUCCESS(f"  Context: id={context.id}"))
        self.stdout.write(self.style.SUCCESS(f"\n→ Open http://127.0.0.1:8000/interpretation/context/{context.id}/ in your browser"))
