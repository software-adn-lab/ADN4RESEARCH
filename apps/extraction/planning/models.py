from django.db import models

from ..shared.audit import AuditModel 

class ExtractionStatusChoices:
    """Opciones para el estado de ExtractionPhase."""
    CONFIG = 'CONFIG'
    OPEN = 'OPEN'
    CLOSED = 'CLOSED'

    CHOICES = [
        (CONFIG, 'Configuración'),
        (OPEN, 'Abierta'),
        (CLOSED, 'Cerrada'),
    ]

class ExtractionPhaseQuerySet(models.QuerySet):
    def open_phases(self):
        return self.filter(status=ExtractionStatusChoices.OPEN)

class ExtractionPhase(AuditModel):
    """Modelo principal que define la configuración y el ciclo de vida de la extracción."""

    project = models.ForeignKey(
        'project.Project',
        on_delete=models.CASCADE,
        related_name='extraction_phases',
        verbose_name="Proyecto Relacionado",
        default=None,
    )
    status = models.CharField(
        max_length=10,
        choices=ExtractionStatusChoices.CHOICES,
        default=ExtractionStatusChoices.CONFIG,
        verbose_name="Estado de la Fase"
    )
    start_date = models.DateField(null=True, blank=True, verbose_name="Fecha de Inicio")
    due_date = models.DateField(null=True, blank=True, verbose_name="Fecha de Vencimiento")
    
    objects = ExtractionPhaseQuerySet.as_manager()

    @property
    def is_tag_list_visible(self) -> bool:
        return self.status in [
            ExtractionStatusChoices.OPEN, 
            ExtractionStatusChoices.CLOSED
        ]
    
    def transition_to_open(self):
        if self.status == ExtractionStatusChoices.OPEN:
            return
            
        self.status = ExtractionStatusChoices.OPEN
        self.save()

    class Meta:
        verbose_name = "Fase de Extracción"
        verbose_name_plural = "Fases de Extracción"

    def __str__(self):
        return f"Fase de Extracción de: {self.project.title} ({self.status})"