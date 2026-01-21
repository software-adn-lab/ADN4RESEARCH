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
    is_active = models.BooleanField(default=False, verbose_name="¿Es Activa?")
    
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
    
    def evaluate_protocol_coverage_and_update_status(self):
        """
        Evalúa si la cobertura del protocolo es 100%.
        Si NO está cubierto completamente, revierte el estado a CONFIG.
        
        Business Rule:
        - Los tags deductivos aprobados deben cubrir todas las preguntas de investigación del protocolo
        - Si la cobertura es < 100%, la fase regresa a CONFIG
        
        Returns:
            bool: True si la cobertura es 100%, False en caso contrario
        """
        from apps.extraction.adapters.design import DesignAdapter
        
        # 1. Obtener RQs del proyecto vía Adapter
        adapter = DesignAdapter()
        protocol_rqs = adapter.get_protocol_questions(self.project_id)
        
        if not protocol_rqs:
            # Si no hay preguntas en el protocolo, considerar como 100% cubierto
            return True
        
        # 2. Extraer IDs de las preguntas del protocolo
        protocol_rq_ids = {rq.id for rq in protocol_rqs}
        
        # 3. Obtener tags deductivos aprobados que cubren estas preguntas
        covered_rq_ids = set(self.tags.filter(
            type='DEDUCTIVE',
            status='APPROVED',
            rq_related_id__in=protocol_rq_ids
        ).values_list('rq_related_id', flat=True))
        
        # 4. Calcular cobertura
        is_fully_covered = (len(covered_rq_ids) == len(protocol_rq_ids))
        
        # 5. Si no está completamente cubierto y la fase NO está en CONFIG, revertir a CONFIG
        if not is_fully_covered and self.status != ExtractionStatusChoices.CONFIG:
            self.status = ExtractionStatusChoices.CONFIG
            self.save()
        
        return is_fully_covered

    class Meta:
        verbose_name = "Fase de Extracción"
        verbose_name_plural = "Fases de Extracción"

    def __str__(self):
        return f"Fase de Extracción de: {self.project.title} ({self.status})"