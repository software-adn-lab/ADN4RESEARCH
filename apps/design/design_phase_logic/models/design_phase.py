from django.db import models
from django.utils import timezone
# REFACTORED: Import BasePhase from Project API (conceptually correct + clean architecture)
from apps.project.api.models import BasePhase


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
        return f"Design Phase: {self.project_id} ({self.current_stage})"

class DesignStageLog(models.Model):
    """
    Trazabilidad: Registra cuándo OCURRIÓ realmente cada etapa.
    Permite historial múltiple si una etapa se reinicia.
    """
    phase = models.ForeignKey(DesignPhase, related_name='stage_logs', on_delete=models.CASCADE)
    stage = models.CharField(max_length=20, choices=DesignPhase.DesignStage.choices)

    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['start_date']
        verbose_name = "Stage Execution Log"

    def close(self):
        self.end_date = timezone.now()
        self.save()

    def __str__(self):
        return f"Log: {self.stage} (Start: {self.start_date.date()})"

class DesignStagePlan(models.Model):
    """
    Planificación (Baseline): Registra cuándo DEBERÍA ocurrir cada etapa.
    Sirve para calcular retrasos y compresiones de cronograma.
    """
    phase = models.ForeignKey(DesignPhase, related_name='planned_stages', on_delete=models.CASCADE)
    stage = models.CharField(max_length=20, choices=DesignPhase.DesignStage.choices)

    planned_start_date = models.DateField()
    planned_end_date = models.DateField()

    class Meta:
        # Constraint Crítico: Evita duplicidad de planes para una misma etapa en un proyecto
        unique_together = ('phase', 'stage')
        ordering = ['planned_start_date']
        verbose_name = "Stage Plan"

    def __str__(self):
        return f"Plan: {self.stage} ({self.planned_start_date} - {self.planned_end_date})"