"""
Management command to seed the database with sample data for testing the UI
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from apps.extraction.core.models import PaperExtraction, Quote, ExtractionStatus
from apps.extraction.taxonomy.models import Tag
from apps.extraction.planning.models import ExtractionPhase, PaperAssignment, ExtractionPhaseStatus


class Command(BaseCommand):
    help = 'Seeds the database with sample data for UI testing'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')
        
        project_id = 1
        
        # Clear existing data
        Quote.objects.all().delete()
        PaperExtraction.objects.all().delete()
        Tag.objects.all().delete()
        PaperAssignment.objects.all().delete()
        ExtractionPhase.objects.all().delete()
        
        # Create extraction phase
        phase = ExtractionPhase.objects.create(
            project_id=project_id,
            status=ExtractionPhaseStatus.ACTIVE,
            end_date=timezone.now().date() + timedelta(days=30),
            auto_close=True,
            activated_at=timezone.now(),
            configured_by_id=1
        )
        self.stdout.write(f'  Created ExtractionPhase: {phase}')
        
        # Create mandatory (deductive) tags
        mandatory_tags = [
            {'name': 'Eficiencia', 'color': '#22c55e', 'question_id': 101},
            {'name': 'Costos', 'color': '#eab308', 'question_id': 102},
            {'name': 'Productividad', 'color': '#3b82f6', 'question_id': 103},
        ]
        
        created_tags = {}
        for tag_data in mandatory_tags:
            tag = Tag.objects.create(
                project_id=project_id,
                name=tag_data['name'],
                color=tag_data['color'],
                type=Tag.TagType.DEDUCTIVE,
                is_mandatory=True,
                is_public=True,
                approval_status=Tag.ApprovalStatus.APPROVED,
                question_id=tag_data['question_id'],
                created_by_id=1
            )
            created_tags[tag.name] = tag
            self.stdout.write(f'  Created mandatory tag: {tag.name}')
        
        # Create public optional tags
        optional_tags = [
            {'name': 'Metodología', 'color': '#8b5cf6'},
            {'name': 'Arquitectura', 'color': '#ec4899'},
            {'name': 'Testing', 'color': '#06b6d4'},
        ]
        
        for tag_data in optional_tags:
            tag = Tag.objects.create(
                project_id=project_id,
                name=tag_data['name'],
                color=tag_data['color'],
                type=Tag.TagType.DEDUCTIVE,
                is_mandatory=False,
                is_public=True,
                approval_status=Tag.ApprovalStatus.APPROVED,
                created_by_id=1
            )
            created_tags[tag.name] = tag
            self.stdout.write(f'  Created optional tag: {tag.name}')
        
        # Create pending inductive tags (from researchers)
        pending_tags = [
            {'name': 'Resistencia al cambio', 'color': '#f97316', 'created_by_id': 10},
            {'name': 'Deuda técnica', 'color': '#ef4444', 'created_by_id': 20},
            {'name': 'Cultura DevOps', 'color': '#14b8a6', 'created_by_id': 30},
        ]
        
        for tag_data in pending_tags:
            tag = Tag.objects.create(
                project_id=project_id,
                name=tag_data['name'],
                color=tag_data['color'],
                type=Tag.TagType.INDUCTIVE,
                is_mandatory=False,
                is_public=False,
                approval_status=Tag.ApprovalStatus.PENDING,
                created_by_id=tag_data['created_by_id']
            )
            created_tags[tag.name] = tag
            self.stdout.write(f'  Created pending tag: {tag.name}')
        
        # Create papers and assignments
        papers = [
            {'study_id': 1, 'title': 'Impacto de TDD en equipos ágiles', 'researcher_id': 10},
            {'study_id': 2, 'title': 'Microservicios vs Monolitos', 'researcher_id': 20},
            {'study_id': 3, 'title': 'DevOps en la industria', 'researcher_id': 30},
            {'study_id': 4, 'title': 'Clean Architecture aplicada', 'researcher_id': 10},
            {'study_id': 5, 'title': 'Refactoring de código legacy', 'researcher_id': 20},
            {'study_id': 6, 'title': 'CI/CD mejores prácticas', 'researcher_id': 30},
        ]
        
        extractions = {}
        for paper in papers:
            extraction = PaperExtraction.objects.create(
                study_id=paper['study_id'],
                project_id=project_id,
                status=ExtractionStatus.IN_PROGRESS,
                assigned_to_id=paper['researcher_id']
            )
            extractions[paper['study_id']] = extraction
            
            # Create assignment
            PaperAssignment.objects.create(
                extraction_phase=phase,
                study_id=paper['study_id'],
                researcher_id=paper['researcher_id'],
                assigned_by_id=1
            )
            self.stdout.write(f'  Created paper extraction: {paper["title"]}')
        
        # Create sample quotes
        sample_quotes = [
            {
                'extraction': extractions[1],
                'text': 'TDD reduce los defectos de software en un 40% según múltiples estudios empíricos realizados en entornos de producción.',
                'location': 'Página 5, Sección 3.1',
                'tags': ['Eficiencia'],
                'researcher_id': 10
            },
            {
                'extraction': extractions[1],
                'text': 'El tiempo inicial de desarrollo aumenta un 15-35%, pero el tiempo total del proyecto se reduce significativamente.',
                'location': 'Página 8, Párrafo 2',
                'tags': ['Costos', 'Productividad'],
                'researcher_id': 10
            },
            {
                'extraction': extractions[2],
                'text': 'La arquitectura de microservicios permite escalar componentes de forma independiente, optimizando recursos.',
                'location': 'Página 12, Sección 4.2',
                'tags': ['Arquitectura', 'Eficiencia'],
                'researcher_id': 20
            },
            {
                'extraction': extractions[3],
                'text': 'La adopción de DevOps incrementa la frecuencia de despliegues en un 200% en promedio.',
                'location': 'Página 3, Abstract',
                'tags': ['Productividad'],
                'researcher_id': 30
            },
            {
                'extraction': extractions[4],
                'text': 'Clean Architecture facilita el testing al desacoplar la lógica de negocio de los frameworks.',
                'location': 'Página 15, Conclusiones',
                'tags': ['Arquitectura', 'Testing'],
                'researcher_id': 10
            },
        ]
        
        for quote_data in sample_quotes:
            quote = Quote.objects.create(
                paper_extraction=quote_data['extraction'],
                text_portion=quote_data['text'],
                location=quote_data['location'],
                researcher_id=quote_data['researcher_id']
            )
            for tag_name in quote_data['tags']:
                if tag_name in created_tags:
                    quote.tags.add(created_tags[tag_name])
            self.stdout.write(f'  Created quote: {quote_data["text"][:50]}...')
        
        # Mark one extraction as complete
        extractions[1].status = ExtractionStatus.DONE
        extractions[1].completed_at = timezone.now()
        extractions[1].save()
        
        self.stdout.write(self.style.SUCCESS('\nDatabase seeded successfully!'))
        self.stdout.write(f'  - {Tag.objects.count()} tags')
        self.stdout.write(f'  - {PaperExtraction.objects.count()} extractions')
        self.stdout.write(f'  - {Quote.objects.count()} quotes')
        self.stdout.write(f'  - {PaperAssignment.objects.count()} assignments')
