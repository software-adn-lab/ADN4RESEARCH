from faker import Faker
from apps.project.models import Project, Stage
from apps.design.research_question.models.research_question import ResearchFramework, ResearchQuestion

fake = Faker()

def create_project(owner):
    return Project.objects.create(
        name="Test Project",
        description="Desc",
        owner=owner
    )

def get_or_create_framework(name, assigned_by, fields=None):
    framework, _ = ResearchFramework.objects.get_or_create(
        name=name,
        defaults={
            "is_global": name in ["PICO","PEO","PCC"],
            "assigned_by": assigned_by,
            "total_fields": len(fields or []),
            "fields": fields or []
        }
    )
    return framework

def create_research_question(framework, project, stage, researcher, suggested, motivation, fields):
    return ResearchQuestion.objects.create(
        research_framework=framework,
        suggested_question=suggested,
        motivation=motivation,
        project=project,
        stage=stage,
        researcher=researcher,
        framework_fields=fields
    )