from faker import Faker
from apps.project.models import Project
from apps.design.research_question.models.research_question import ResearchQuestion

fake = Faker()

def create_project(owner):
    return Project.objects.create(
        name="Test Project",
        description="Desc",
        owner=owner
    )