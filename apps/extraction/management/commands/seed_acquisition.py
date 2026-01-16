# apps/acquisition/management/commands/seed_acquisition.py
import random
import uuid
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model
from django.apps import apps
from faker import Faker

# Importamos los modelos de Acquisition
from apps.acquisition.models import StudyModel, SearchExecutionModel, ExecutionStudy

# Configuración de Faker
fake = Faker(['es_ES', 'en_US'])

class Command(BaseCommand):
    help = 'Puebla la base de datos de Acquisition con datos de prueba (Studies, Executions)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strategy_id',
            type=int,
            default=1,
            help='ID de la SearchStrategy a la que se vincularán las ejecuciones (Default: 1)'
        )
        parser.add_argument(
            '--studies',
            type=int,
            default=3,
            help='Cantidad de estudios a crear'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Iniciando proceso de seeding para Acquisition...'))

        strategy_id = options['strategy_id']
        studies_count = options['studies']
        
        # 1. Obtener Dependencias Externas (Strategy y User)
        # Usamos apps.get_model para evitar errores de importación circular o si la app design no está cargada
        SearchStrategy = apps.get_model('design', 'SearchStrategy')
        User = get_user_model()

        try:
            # Intentamos obtener la estrategia (Asumimos que existe según tu indicación)
            strategy = SearchStrategy.objects.get(pk=strategy_id)
            self.stdout.write(self.style.SUCCESS(f'✓ Estrategia encontrada: ID {strategy.pk}'))
        except SearchStrategy.DoesNotExist:
            raise CommandError(
                f"No existe una SearchStrategy con ID {strategy_id}. "
                "Por favor crea una estrategia primero o pasa un ID válido con --strategy_id"
            )

        # Obtenemos un usuario para la auditoría (o el primero que encontremos)
        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.WARNING('⚠ No hay usuarios en el sistema. Creando execution sin usuario.'))

        # 2. Ejecutar en transacción atómica para integridad
        with transaction.atomic():
            
            # --- Paso A: Crear Estudios (StudyModel) ---
            created_studies = []
            sources = ['Scopus', 'IEEE Xplore', 'Web of Science', 'PubMed']
            statuses = ['discovered', 'enriched', 'downloaded', 'failed']
            
            self.stdout.write(f'Creando {studies_count} estudios...')
            
            for _ in range(studies_count):
                study = StudyModel.objects.create(
                    title=fake.sentence(nb_words=10).replace('.', ''),
                    link=fake.url(),
                    source=random.choice(sources),
                    doi=f"10.{fake.random_number(digits=4)}/{fake.slug()}",
                    status=random.choice(statuses),
                    # Feature 3: Metadata
                    authors=[fake.name() for _ in range(random.randint(1, 5))],
                    abstract=fake.paragraph(nb_sentences=5),
                    year=fake.year(),
                    journal=fake.company(),
                    keywords=[fake.word() for _ in range(random.randint(3, 8))],
                    # Feature 4: Full Text
                    pdf_path=f"/media/papers/{fake.uuid4()}.pdf" if random.choice([True, False]) else None,
                    download_status="texto_completo_disponible" if random.choice([True, False]) else "pendiente",
                    page_count=random.randint(5, 25),
                    field_origins={'doi': 'automated', 'title': 'scopus_api'}
                )
                created_studies.append(study)

            self.stdout.write(self.style.SUCCESS(f'✓ {len(created_studies)} Estudios creados.'))

            # --- Paso B: Crear Ejecución (SearchExecutionModel) ---
            execution = SearchExecutionModel.objects.create(
                strategy=strategy,
                executed_by=user,
                translated_queries={
                    "scopus": f"TITLE-ABS-KEY({fake.word()})",
                    "ieee": f"({fake.word()} AND {fake.word()})"
                },
                results_count=studies_count,
                new_studies_count=studies_count, # Asumimos todos nuevos para el seed
                status='SUCCESS'
            )
            self.stdout.write(self.style.SUCCESS(f'✓ Ejecución creada: {execution.id}'))

            # --- Paso C: Vincular Estudios a Ejecución (ExecutionStudy) ---
            links_to_create = []
            for i, study in enumerate(created_studies):
                links_to_create.append(
                    ExecutionStudy(
                        execution=execution,
                        study=study,
                        is_new=True,
                        providers=[study.source],
                        rank_position=i + 1
                    )
                )
            
            # Bulk create es mucho más eficiente
            ExecutionStudy.objects.bulk_create(links_to_create)
            self.stdout.write(self.style.SUCCESS(f'✓ {len(links_to_create)} Vinculaciones creadas.'))

        self.stdout.write(self.style.SUCCESS('--------------------------------------'))
        self.stdout.write(self.style.SUCCESS('SEEDING COMPLETADO EXITOSAMENTE 🚀'))
        self.stdout.write(self.style.SUCCESS('--------------------------------------'))