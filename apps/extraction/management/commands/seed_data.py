import random
import uuid
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from faker import Faker

# --- MODELOS ---
from apps.project.structure.models.project_models import Project
from apps.design.research_question.models.research_question import ResearchQuestion
from apps.design.shared.models.design_phase import DesignPhase
from apps.extraction.planning.models import ExtractionPhase, ExtractionStatusChoices
from apps.extraction.core.models import PaperExtraction, PaperExtractionStatusChoices

# Modelos actualizados de Adquisición
from apps.acquisition.models import StudyModel 
# from apps.acquisition.models import SearchExecutionModel, ExecutionStudy # Descomentar cuando tengamos Strategy

User = get_user_model()

class Command(BaseCommand):
    help = 'Puebla la BD. NOTA: Los estudios se crean pero no se vinculan a ejecuciones por falta de SearchStrategy.'

    def add_arguments(self, parser):
        parser.add_argument('--projects', type=int, default=1, help='Número de proyectos')

    def handle(self, *args, **options):
        fake = Faker(['es_ES'])
        num_projects = options['projects']
        
        # Fuentes académicas simuladas
        SOURCES = ['Scopus', 'IEEE Xplore', 'Web of Science', 'ACM Digital Library']

        self.stdout.write(self.style.WARNING(f'Iniciando seeding para {num_projects} proyecto(s)...'))

        try:
            with transaction.atomic():
                # 1. Usuarios
                owner, _ = User.objects.get_or_create(
                    username='owner_user',
                    defaults={'email': 'owner@test.com', 'password': 'password123'}
                )
                if _: owner.set_password('password123'); owner.save()

                researcher, _ = User.objects.get_or_create(
                    username='researcher_user',
                    defaults={'email': 'dev@test.com', 'password': 'password123'}
                )
                if _: researcher.set_password('password123'); researcher.save()

                for i in range(num_projects):
                    # 2. Proyecto
                    project = Project.objects.create(
                        title=f"Proyecto: {fake.catch_phrase()}",
                        summary=fake.paragraph(),
                        motivation=fake.paragraph(),
                        general_objective=fake.sentence(),
                        owner=owner
                    )
                    self.stdout.write(f"-- Proyecto: {project.title}")

                    # 3. Design Phase
                    design_phase = DesignPhase.objects.create(
                        project=project,
                        current_stage=DesignPhase.DesignStage.FINISHED
                    )

                    # 4. RQs
                    for _ in range(2):
                        ResearchQuestion.objects.create(
                            design_phase=design_phase,
                            question=f"¿{fake.sentence()}?",
                            researcher=researcher,
                            status='APPROVED'
                        )

                    # 5. Extraction Phase
                    extraction_phase = ExtractionPhase.objects.create(
                        project=project,
                        status=ExtractionStatusChoices.CONFIG
                    )

                    # 6. Crear Estudios y vincularlos mediante PaperExtraction
                    for _ in range(5): 
                        # A. Crear el estudio académico (Acquisition)
                        study = StudyModel.objects.create(
                            title=fake.sentence(nb_words=10),
                            link=fake.url(),
                            source=random.choice(['Scopus', 'IEEE', 'WoS']),
                            doi=f"10.{fake.random_number(digits=4)}/{fake.bothify(text='????-####')}",
                            status='discovered',
                            authors=[fake.name() for _ in range(2)],
                            year=int(fake.year())
                        )

                        # B. VINCULAR AL PROYECTO (Core Extraction) <-- ESTO ES LO QUE FALTA
                        # Creamos la entidad que el Dashboard realmente lee
                        PaperExtraction.objects.create(
                            study=study,
                            extraction_phase=extraction_phase,
                            status=PaperExtractionStatusChoices.PENDING,
                            assigned_to=researcher, # Se lo asignamos al investigador del seeder
                            path=study.link # Usamos el link como path inicial
                        )

                    self.stdout.write(f"   --- 5 Estudios y 5 Extracciones (Papers) creados.")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
            raise e

        self.stdout.write(self.style.SUCCESS('¡Seeding completado!'))