#!/usr/bin/env python
"""
Initialize a SelectionPhase for testing
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.project.structure.models.project_models import Project
from apps.selection.models import SelectionPhase

def main():
    project = Project.objects.first()
    if not project:
        print("No project found. Please create a project first.")
        return
    
    print(f'Initializing SelectionPhase for project: {project.title}')
    
    selection_phase, created = SelectionPhase.objects.get_or_create(
        project=project,
        defaults={
            'is_active': True,
        }
    )
    
    if created:
        print(f'✅ Created SelectionPhase (ID: {selection_phase.project_id})')
    else:
        print(f'ℹ️  SelectionPhase already exists (ID: {selection_phase.project_id})')
    
    print(f'   - Active: {selection_phase.is_active}')
    print(f'   - Status: {selection_phase.status}')
    print(f'   - Current stage: {selection_phase.current_stage}')
    print(f'\n✅ SelectionPhase is ready!')
    print(f'   URL: /project/{project.id}/selection/')

if __name__ == '__main__':
    main()
