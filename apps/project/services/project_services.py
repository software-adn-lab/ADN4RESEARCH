from project.models import Project, Stage

class ProjectService:
    def add_member(self, project: Project, user, role):
        # Implementation to add a member to the project with a specific role
        project.add_member(user, role)
    
    def get_members(self, project: Project):
        return project.get_members()
    

    def open_stage(self, stage: Stage):
        # Implementation to open a stage of the project
        stage.status = "OPENED"
        stage.save()

    def is_stage_opened(self, stage):
        return stage.status == "OPENED"
    
    def get_project_members(self, project):
        return project.get_members()
    
    
