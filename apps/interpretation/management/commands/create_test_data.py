import random
import uuid
from django.core.management.base import BaseCommand

from apps.project.structure.models.project_models import Project
from apps.design.design_phase_logic.models.design_phase import DesignPhase
from apps.design.research_question.models.research_question import ResearchQuestion
from apps.design.search_strategy.models.search_strategy import SearchStrategy
from apps.acquisition.models import SearchExecutionModel, StudyModel
from apps.extraction.core.models import PaperExtraction, Quote
from apps.extraction.taxonomy.models import Tag
from apps.interpretation.conclusion_assistant.models.theme_models import Theme
from apps.interpretation.conclusion_assistant.models.subtheme_models import SubTheme
from apps.interpretation.conclusion_assistant.models.normalization_models import (
    NormalizedCode,
)


class Command(BaseCommand):
    help = "Generates test data for the Interpretation Dashboard"

    def handle(self, *args, **kwargs):
        self.stdout.write('Generating test data...')

        # 0. Ensure a user exists
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write(f"Created test user: testuser / testpass123")

        # 1. Create Project & Design Structure
        project_title = f"Test Visualization {random.randint(1000, 9999)}"
        project, _ = Project.objects.get_or_create(
            name=project_title,
            defaults={
                'description': 'Generated data for testing charts and matrix.',
                'owner': user
            }
        )

        design, _ = DesignPhase.objects.get_or_create(project=project)
        rq, _ = ResearchQuestion.objects.get_or_create(
            design_phase=design,
            defaults={"question": "What are the impacts of AI in Education?"},
        )
        strategy, _ = SearchStrategy.objects.get_or_create(
            research_question=rq, defaults={"status": "APPROVED"}
        )
        execution, _ = SearchExecutionModel.objects.get_or_create(
            strategy=strategy, defaults={"results_count": 15}
        )

        self.stdout.write(f"Project created: {project.name} (ID: {project.id})")

        # 2. Create Studies (Acquisition)
        sources = [
            "IEEE Access",
            "Computers & Education",
            "British Journal of EdTech",
            "ACM Transactions",
        ]
        studies = []

        for i in range(15):
            year = random.choice([2020, 2021, 2022, 2023, 2024])
            study = StudyModel.objects.create(
                title=f"Impact of AI on Student Performance #{i+1}",
                year=year,
                source=random.choice(sources),
                authors=[f"Researcher {chr(65+i)}", "Doe J."],
                abstract="This study analyzes how AI tools influence student grades...",
                doi=f"10.1016/j.test.{i}",
                uuid=uuid.uuid4(),
            )
            # Link study to execution
            # Note: ExecutionStudy is the through model, but we can use the related manager if defined
            # Or create ExecutionStudy explicitly if needed.
            # Checking models.py: studies = models.ManyToManyField(StudyModel, through='ExecutionStudy'...)
            from apps.acquisition.models import ExecutionStudy

            ExecutionStudy.objects.create(execution=execution, study=study, is_new=True)

            studies.append(study)

        self.stdout.write(f"Created {len(studies)} studies.")

        # 3. Create Interpretation Structure (Themes & Codes)

        # Theme A: Personalization
        theme_pers, _ = Theme.objects.get_or_create(
            name="Personalization",
            created_by=user,
            defaults={'research_question': "How does AI personalize education?"}
        )
        # We need to link theme to project somehow?
        # Theme model doesn't have project_id in the snippet I read,
        # but SubTheme -> Theme.
        # Wait, ThemeDiscoveryProposal has project.
        # Let's check Theme model again. It has created_by.
        # Usually Themes are linked to context or project.
        # Assuming for this test we just create them.

        subtheme_adapt, _ = SubTheme.objects.get_or_create(
            theme=theme_pers, name="Adaptive Learning"
        )

        # Theme B: Ethics
        theme_eth, _ = Theme.objects.get_or_create(
            name="Ethical Concerns",
            created_by=user,
            defaults={'research_question': "What are the ethical concerns?"}
        )
        subtheme_bias, _ = SubTheme.objects.get_or_create(
            theme=theme_eth, name="Algorithmic Bias"
        )

        # Normalized Codes (The bridge)
        # Code for Adaptive Learning
        norm_adapt, _ = NormalizedCode.objects.get_or_create(
            project=project,
            code="TECH_ADAPTIVE",
            defaults={"original_codes": ["adaptive", "customization", "tailored"]},
        )
        subtheme_adapt.central_codes = ["TECH_ADAPTIVE"]
        subtheme_adapt.save()

        # Code for Bias
        norm_bias, _ = NormalizedCode.objects.get_or_create(
            project=project,
            code="ETHIC_BIAS",
            defaults={"original_codes": ["bias", "fairness", "discrimination"]},
        )
        subtheme_bias.central_codes = ["ETHIC_BIAS"]
        subtheme_bias.save()

        # 4. Create Extractions & Evidence (Extraction)
        tags_adapt = ["adaptive", "customization"]
        tags_bias = ["bias", "fairness"]

        for idx, study in enumerate(studies[:10]):
            try:
                # Note: PaperExtraction.study_id is IntegerField, StudyModel.uuid is UUID.
                # This will likely fail or store a truncated value if we try to put UUID in IntegerField.
                # For the purpose of this script, we will try to create it, but be aware of the schema mismatch.
                # If we can't store the UUID, the matrix won't link.

                # We'll use the UUID directly now that the model supports it.

                extraction = PaperExtraction.objects.create(
                    study_id=study.uuid, project_id=project.id, status="Done"
                )

                # Create Quotes and Tags
                if idx % 2 == 0:
                    quote = Quote.objects.create(
                        paper_extraction=extraction,
                        text_portion="The system adapted to the student's pace.",
                        location="Results",
                        researcher_id=user.id
                    )
                    # Quote model fields: paper_extraction, text_portion, location, researcher_id, validated
                    # It doesn't seem to have user_id/object_id/content_type based on previous read_file

                    tag_name = random.choice(tags_adapt)
                    tag, _ = Tag.objects.get_or_create(
                        name=tag_name,
                        project_id=project.id,
                        defaults={'created_by_id': user.id}
                    )
                    quote.tags.add(tag)

                if idx % 3 == 0:
                    quote = Quote.objects.create(
                        paper_extraction=extraction,
                        text_portion="We observed bias in the selection process.",
                        location="Discussion",
                        researcher_id=user.id
                    )
                    tag_name = random.choice(tags_bias)
                    tag, _ = Tag.objects.get_or_create(
                        name=tag_name,
                        project_id=project.id,
                        defaults={'created_by_id': user.id}
                    )
                    quote.tags.add(tag)

            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping extraction for study {study.title}: {e}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS("------------------------------------------------")
        )
        self.stdout.write(self.style.SUCCESS(f"Data generation complete!"))
        self.stdout.write(self.style.SUCCESS(f"Project ID: {project.id}"))
        self.stdout.write(
            self.style.SUCCESS(
                f"Access the dashboard at: /interpretation/dashboard/{project.id}/"
            )
        )
        self.stdout.write(
            self.style.SUCCESS("------------------------------------------------")
        )
