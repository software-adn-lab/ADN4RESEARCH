from django.core.management.base import BaseCommand

from django.contrib.auth import get_user_model

from apps.interpretation.conclusion_assistant.models.theme_models import Theme
from apps.interpretation.conclusion_assistant.models.subtheme_models import SubTheme
from apps.interpretation.conclusion_assistant.services.interpretation_services import InterpretationService


class Command(BaseCommand):
    help = "Create a demo Theme, SubTheme and start an InterpretationContext. Prints created IDs and conversation URL path."

    def handle(self, *args, **options):
        svc = InterpretationService()

        # Find an existing user to set as created_by; if none exists, create a demo superuser.
        User = get_user_model()
        user = User.objects.filter(is_superuser=True).first() or User.objects.filter(is_staff=True).first() or User.objects.first()
        if not user:
            # Create a demo superuser with a simple password — instruct the developer to change it.
            user = User.objects.create_superuser(username="demo", email="demo@example.com", password="demo123")
            self.stdout.write(self.style.WARNING("No existing users found — created demo superuser 'demo' with password 'demo123'. Change this in production."))

        theme = Theme.objects.create(
            name="Antipatrones en el desarrollo de software",
            research_question=(
                "¿Cuáles son los desafíos técnicos y organizacionales reportados al implementar DevOps en equipos distribuidos?"
            ),
            created_by=user,
        )

        sub = SubTheme.objects.create(
            theme=theme,
            name="Subtema B: Retos Culturales y de Comunicación",
            central_codes=["Comunicación asíncrona", "Zonas horarias"],
            key_citations=["Autor et al., 2020: ejemplo de cita"],
        )

        context, trace = svc.initiate_interpretation_context(sub)

        self.stdout.write(self.style.SUCCESS(f"Created Theme id={theme.id}, SubTheme id={sub.id}, Context id={context.id}"))
        self.stdout.write(self.style.SUCCESS(f"Open /interpretation/context/{context.id}/ in your browser"))
