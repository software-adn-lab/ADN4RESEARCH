
class ProjectService:
    def add_member(self, project, user, role):
        # Implementation to add a member to the project with a specific role
        project.add_member(user, role)

    def open_stage(self, stage, opened_by, due_time):
        # Implementation to open a stage of the project
        stage.status = "OPENED"
        stage.opened_by = opened_by
        stage.due_time = due_time
        stage.save()

    def is_stage_opened(self, stage):
        return stage.status == "OPENED"
    
    def get_project_members(self, project):
        return project.get_members()
    
    