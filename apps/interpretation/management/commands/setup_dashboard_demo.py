"""
Django management command to set up test data for Results Dashboard.

Usage:
    python manage.py setup_dashboard_demo
"""
import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

# Models
from apps.project.structure.models.project_models import Project
from apps.design.design_phase_logic.models.design_phase import DesignPhase
from apps.design.research_question.models.research_question import ResearchQuestion
from apps.design.search_strategy.models.search_strategy import SearchStrategy
from apps.acquisition.models import SearchExecutionModel, StudyModel, ExecutionStudy
from apps.extraction.planning.models import ExtractionPhase, ExtractionStatusChoices
from apps.extraction.taxonomy.models import Tag, TagTypeChoices, ApprovalStatusChoices
from apps.extraction.core.models import PaperExtraction, Quote, PaperExtractionStatusChoices

User = get_user_model()


class Command(BaseCommand):
    help = "Creates dummy extraction data for testing Interpretation Dashboard"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("→ Setting up Dashboard data..."))

        # 1. Get Project & User
        try:
            project = Project.objects.get(id=4)
            user = User.objects.get(username="demo_user")
        except Project.DoesNotExist:
            self.stdout.write(self.style.ERROR("Project ID 4 not found. Run setup_theme_discovery_demo first."))
            return
        
        self.stdout.write(f"  • Using project: {project.title}")

        # 2. Design Phase & RQ & Strategy
        design_phase, _ = DesignPhase.objects.get_or_create(project=project, defaults={'is_active': True})
        
        rq, _ = ResearchQuestion.objects.get_or_create(
            design_phase=design_phase,
            question="What are the effects of AI in Software Engineering?",
            defaults={'status': 'APPROVED', 'researcher': user}
        )
        
        strategy, _ = SearchStrategy.objects.get_or_create(
            research_question=rq,
            defaults={'final_search_string':"AI AND 'Software Engineering'", 'created_by': user}
        )
        
        # 3. Execution
        execution = SearchExecutionModel.objects.create(strategy=strategy, status='SUCCESS')
        
        # 4. Studies
        sources = ['IEEE Xplore', 'Scopus', 'ACM Digital Library', 'PubMed']
        studies = []
        
        # Create 15 dummy studies
        for i in range(1, 16):
            study = StudyModel.objects.create(
                title=f"Study {i}: AI-driven Theme Discovery for Systematic Reviews",
                source=random.choice(sources),
                year=random.randint(2018, 2024),
                authors=[f"Author {i}A", f"Author {i}B"],
                abstract=f"This study investigates the usage of AI in context {i}...",
                doi=f"10.1145/example.{i}"
            )
            ExecutionStudy.objects.create(
                execution=execution, 
                study=study, 
                is_new=True
            )
            studies.append(study)
            
        self.stdout.write(f"  • Created {len(studies)} studies linked to acquisition channel.")

        # 5. Extraction Phase
        ext_phase, created = ExtractionPhase.objects.get_or_create(
            project=project, 
            defaults={
                'status': ExtractionStatusChoices.OPEN,
                'start_date': timezone.now().date()
            }
        )
        
        # 6. Tags (Taxonomy)
        tag_names = ['Methodology', 'Results', 'Challenges', 'Future Work', 'Tool Support']
        tags = []
        for name in tag_names:
            t, _ = Tag.objects.get_or_create(
                name=name, 
                extraction_phase=ext_phase, 
                defaults={
                    'type': TagTypeChoices.DEDUCTIVE, 
                    'status': ApprovalStatusChoices.APPROVED,
                    'color': '#3b82f6', # blue-500
                    'created_by': user
                }
            )
            tags.append(t)
            
        # 7. Paper Extractions & Quotes
        self.stdout.write("  • Generating extraction data...")
        count_quotes = 0
        
        for study in studies:
            # Randomly decide status: 80% completed, 20% in progress
            status = PaperExtractionStatusChoices.COMPLETED if random.random() > 0.2 else PaperExtractionStatusChoices.IN_PROGRESS
            
            pe, _ = PaperExtraction.objects.get_or_create(
                study=study, 
                extraction_phase=ext_phase,
                defaults={'status': status, 'assigned_to': user}
            )
            
            # If completed, create some synthetic quotes
            if status == PaperExtractionStatusChoices.COMPLETED:
                for _ in range(random.randint(2, 5)):
                    q = Quote.objects.create(
                        paper_extraction=pe, 
                        text_fragment=f"Evidence found in {study.title} regarding {random.choice(tag_names)}...",
                        location={"page": random.randint(1, 15)},
                        created_by=user
                    )
                    # Assign 1 or 2 tags
                    chosen_tags = random.sample(tags, k=random.randint(1, 2))
                    q.tags.set(chosen_tags)
                    count_quotes += 1

        self.stdout.write(self.style.SUCCESS(f"✓ Dashboard Data Setup Complete!"))
        self.stdout.write(f"  • Studies: {len(studies)}")
        self.stdout.write(f"  • Quotes: {count_quotes}")
        self.stdout.write(f"  • Extraction Phase: {ext_phase.status}")
