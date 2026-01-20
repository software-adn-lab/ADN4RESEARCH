import os
import django
import sys

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.project.structure.models.project_models import Project
from apps.interpretation.conclusion_assistant.models.phase_models import InterpretationPhase

def activate_interpretation_for_all_projects():
    projects = Project.objects.all()
    print(f"Found {projects.count()} projects.")
    
    for project in projects:
        print(f"Checking project: {project.title} (ID: {project.id})")
        
        phase, created = InterpretationPhase.objects.get_or_create(
            project=project,
            defaults={
                'is_active': True
            }
        )
        
        if created:
            print(f"  - Created new InterpretationPhase.")
        else:
            print(f"  - InterpretationPhase already exists.")
            if not phase.is_active:
                phase.is_active = True
                phase.save()
                print(f"  - Activated InterpretationPhase.")
            else:
                print(f"  - InterpretationPhase is already active.")

if __name__ == '__main__':
    activate_interpretation_for_all_projects()
