from django.db import models
from apps.project.api.models import BasePhase

class InterpretationPhase(BasePhase):
    project = models.OneToOneField(
        'project.Project',
        on_delete=models.CASCADE,
        related_name='interpretation_phase'
    )
    
    class Meta:
        verbose_name = "Interpretation Phase"
        verbose_name_plural = "Interpretation Phases"
        app_label = 'interpretation' # Explicitly set app_label just in case

    def __str__(self):
        return f"Interpretation Phase for {self.project.title}"
