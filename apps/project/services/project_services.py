from apps.design.research_question.models.research_question import ResearchFramework
from apps.project.models import Project, Stage


class ProjectService:
    def add_member(self, project: Project, user, role):
        # Implementation to add a member to the project with a specific role
        project.add_member(user, role)

    def get_members(self, project: Project):
        return project.get_members()

    def get_project_framework(self, request):
        # Implementation to get the research framework associated with the project
        user = request.user
        project = Project.objects.filter(memberships__user=user).first()
        if project:
            return project.research_framework
        return None

    def asign_research_framework_to_project(self, project: Project, framework):
        print("Assigning framework to project...", project, framework)
        project.research_framework = framework
        project.save()

    def open_stage(self, stage: Stage, opened_by, due_time):
        # Implementation to open a stage of the project
        stage.opened_by = opened_by
        stage.due_time = due_time
        stage.status = "OPENED"
        stage.save()

    def close_stage(self, stage: Stage, closed_by):
        # Implementation to close a stage of the project
        stage.closed_by = closed_by
        stage.status = "CLOSED"
        stage.save()

    def is_stage_opened(self, stage):
        return stage.status == "OPENED"

    def get_project_members(self, project):
        return project.get_members()

    def get_or_create_framework(self, framework_name, assigned_by) -> ResearchFramework:
        research_framework, _created = ResearchFramework.objects.get_or_create(
            name=framework_name,
            defaults={
                "is_global": framework_name in ["PICO", "PEO", "PCC"],
                "assigned_by": assigned_by,
            }
        )
        return research_framework
