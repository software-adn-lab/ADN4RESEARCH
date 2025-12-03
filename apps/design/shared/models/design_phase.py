from django.db import models
from django.utils import timezone
from apps.project.models import BasePhase

class DesignPhaseQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)
    
    def by_project(self, project_id):
        return self.filter(pk=project_id)

class DesignPhase(BasePhase):
    class DesignStage(models.TextChoices):
        RQ_CREATION = 'RQ_CREATION', 'Research Question Creation'
        RQ_DISCUSSION = 'RQ_DISCUSSION', 'Discussion'
        CRITERIA_DEFINITION = 'CRITERIA_DEFINITION', 'Eligibility Criteria Definition' 
        SEARCH_STRATEGY = 'SEARCH_STRATEGY', 'Search Strategy Building'
        FINISHED = 'FINISHED', 'Finalized'

    RQ_EDITION_STAGES = [
        DesignStage.RQ_CREATION,
        DesignStage.RQ_DISCUSSION,
    ]
    
    DESIGN_FLOW = [
            DesignStage.RQ_CREATION, 
            DesignStage.RQ_DISCUSSION, 
            DesignStage.CRITERIA_DEFINITION,
            DesignStage.SEARCH_STRATEGY,
            DesignStage.FINISHED
    ]

    project = models.OneToOneField('project.Project', related_name='design_phase', on_delete=models.CASCADE, primary_key=True)
    current_stage = models.CharField(max_length=20, choices=DesignStage.choices, default=DesignStage.RQ_CREATION)
    objects = DesignPhaseQuerySet.as_manager()

    def save(self, *args, **kwargs):
        self.full_clean()
        # Si llegamos a FINISHED, cerramos la fase automáticamente
        if self.current_stage == self.DesignStage.FINISHED:
            self.is_active = False
            self.end_date = timezone.now()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Design Phase for {self.project_id}"