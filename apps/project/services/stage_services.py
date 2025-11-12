from apps.project.models import Stage


class StageService:
    def create_stage(self, project, name, opened_by, due_time):
        stage = Stage.objects.create(
            project=project,
            name=name,
            status=Stage.Status.OPEN,
            opened_by=opened_by,
            due_time=due_time
        )
        stage.save()
        return stage
    
    def close_stage(self, stage, closed_by):
        stage.status = Stage.Status.CLOSED
        stage.closed_by = closed_by
        stage.save()
    
    def is_stage_opened(self, stage):
        return stage.status == Stage.Status.OPEN
    
    
    
    
    