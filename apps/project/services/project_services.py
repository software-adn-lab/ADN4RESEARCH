from apps.project.models import Project, ResearchFramework

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
        project.research_framework = framework
        project.save()

    def get_project_members(self, project):
        return project.get_members()

    def assign_framework_project(self, project_id, framework_name, fields_data, assigned_by) -> ResearchFramework:
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise ValueError(f"Project with id {project_id} does not exist")

        research_framework, created = ResearchFramework.objects.get_or_create(
            name=framework_name,
            assigned_by=assigned_by,
            fields_data=fields_data,
        )

        if not created and fields_data:
            research_framework.fields_data = fields_data
            research_framework.save()

        project.research_framework = research_framework
        project.save()
        return research_framework
