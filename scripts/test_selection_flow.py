#!/usr/bin/env python
"""
Test paper distribution and screening flow
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.project.structure.models.project_models import Project
from apps.project.facade import get_project_facade

def main():
    project = Project.objects.first()
    if not project:
        print("❌ No project found")
        return
    
    print(f'Testing project: {project.title} (ID: {project.id})')
    
    # Test project facade
    facade = get_project_facade()
    
    try:
        studies = facade.get_studies_by_project(
            project_id=project.id,
            include_metadata=True
        )
        
        print(f'\n✅ Project facade working!')
        print(f'   Found {len(studies)} studies')
        
        if studies:
            print('\n📄 Sample studies:')
            for study in studies[:3]:
                title = (study.get('title') or 'No title')[:60]
                abstract = study.get('abstract') or ''
                abstract_len = len(abstract)
                print(f'   - {title}... (abstract: {abstract_len} chars)')
        else:
            print('\n⚠️  No studies found. You need to:')
            print('   1. Complete Design phase')
            print('   2. Run search executions in Acquisition')
            print('   3. Enrich the discovered studies')
        
        # Test distribution service
        from apps.selection.features.distribution.metadata.services import PaperDistributionService
        
        if len(studies) > 0:
            print(f'\n🔄 Testing distribution service...')
            service = PaperDistributionService(project.id)
            
            try:
                distribution = service.distribute_papers(total_reviews_per_paper=2)
                print(f'✅ Distribution successful!')
                print(f'\n📊 Distribution results:')
                for username, paper_ids in distribution.items():
                    print(f'   - {username}: {len(paper_ids)} papers')
            except ValueError as e:
                print(f'⚠️  Distribution failed: {e}')
        
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
