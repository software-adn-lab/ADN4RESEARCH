from django.db import models
from django.utils.translation import gettext_lazy as _


class ExtractionPhaseStatus(models.TextChoices):
    """Estados posibles de la fase de extracción"""
    CONFIGURATION = 'configuration', _('Configuración')
    ACTIVE = 'active', _('Activa')
    CLOSED = 'closed', _('Cerrada')


class ExtractionPhase(models.Model):
    """
    Configuración de la fase de extracción para un proyecto.
    Solo puede existir una fase de extracción por proyecto.
    """
    project_id = models.IntegerField(unique=True, db_index=True)
    
    status = models.CharField(
        max_length=20,
        choices=ExtractionPhaseStatus.choices,
        default=ExtractionPhaseStatus.CONFIGURATION
    )
    
    # Configuración de fechas
    end_date = models.DateField(null=True, blank=True)
    auto_close = models.BooleanField(
        default=False,
        help_text="Si True, la fase se cierra automáticamente al llegar a end_date"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    # Usuario que configuró/activó (referencia débil)
    configured_by_id = models.IntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "Extraction Phase"
        verbose_name_plural = "Extraction Phases"

    def __str__(self):
        return f"ExtractionPhase (Project {self.project_id}) - {self.status}"

    @property
    def is_configurable(self) -> bool:
        """La fase puede configurarse si está en estado de configuración"""
        return self.status == ExtractionPhaseStatus.CONFIGURATION

    @property
    def is_active(self) -> bool:
        return self.status == ExtractionPhaseStatus.ACTIVE

    @property
    def is_closed(self) -> bool:
        return self.status == ExtractionPhaseStatus.CLOSED


class PaperAssignment(models.Model):
    """
    Asignación de un paper a un Researcher para extracción.
    Relaciona el study_id (del módulo Acquisition) con un researcher_id.
    """
    extraction_phase = models.ForeignKey(
        ExtractionPhase,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    
    # Referencias débiles a entidades externas
    study_id = models.IntegerField(db_index=True)  # Paper del módulo Acquisition
    researcher_id = models.IntegerField(db_index=True)  # User del módulo Identity
    
    # Metadata
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by_id = models.IntegerField(null=True, blank=True)  # Owner que asignó
    
    class Meta:
        unique_together = [['extraction_phase', 'study_id']]
        indexes = [
            models.Index(fields=['researcher_id', 'extraction_phase']),
        ]

    def __str__(self):
        return f"Paper {self.study_id} -> Researcher {self.researcher_id}"
