

from apps.project.models import Project, Stage


class ProjectService:
    def add_member(self, project: Project, user, role):
        # Implementation to add a member to the project with a specific role
        project.add_member(user, role)
    
    def get_members(self, project: Project):
        return project.get_members()
    
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
    
    
