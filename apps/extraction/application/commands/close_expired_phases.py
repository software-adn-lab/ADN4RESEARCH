from django.core.management.base import BaseCommand
from apps.extraction.container import container


class Command(BaseCommand):
    help = 'Cierra automáticamente fases de extracción que ya pasaron su end_date'

    def handle(self, *args, **options):
        phases = container.phase_repository.get_active_phases_to_close()

        closed_count = 0
        for phase in phases:
            if phase.auto_close_if_needed():
                container.phase_repository.save(phase)
                closed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Fase cerrada: Project {phase.project_id}'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Total de fases cerradas: {closed_count}'
            )
        )