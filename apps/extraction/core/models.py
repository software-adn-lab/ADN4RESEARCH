from django.db import models
from django.conf import settings
from ..shared.audit import AuditModel

class PaperExtractionStatusChoices:
    """Opciones para el estado de PaperExtraction."""
    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'

    CHOICES = [
        (PENDING, 'Pendiente'),
        (IN_PROGRESS, 'En Progreso'),
        (COMPLETED, 'Completado'),
    ]


class PaperExtractionQuerySet(models.QuerySet):
    def completed(self):
        return self.filter(status=PaperExtractionStatusChoices.COMPLETED)

    def by_study(self, study_id):
        return self.filter(study_id=study_id)


class PaperExtraction(AuditModel):
    """Representa un archivo PDF o documento de donde se extraerá la información."""

    study = models.ForeignKey(
        'acquisition.StudyModel',
        on_delete=models.CASCADE,
        related_name='paper_extractions',
        verbose_name="Estudio Relacionado (Acquisition)",
        null=True,
    )
    extraction_phase = models.ForeignKey(
        'extraction.ExtractionPhase',
        on_delete=models.CASCADE,
        related_name='papers_to_extract',
        verbose_name="Fase de Extracción",
        default=1,
    )
    status = models.CharField(
        max_length=15,
        choices=PaperExtractionStatusChoices.CHOICES,
        default=PaperExtractionStatusChoices.PENDING,
        verbose_name="Estado de la Extracción"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_extractions',
        verbose_name="Asignado A"
    )
    path = models.CharField(
        max_length=500, 
        verbose_name="Ruta o URL del Documento", 
        null=True,  # Permite valores nulos si el path no es obligatorio
        blank=True,  # Permite que el campo esté vacío, si es necesario
    )

    objects = PaperExtractionQuerySet.as_manager()

    def get_missing_mandatory_tags(self):
        """
        Tags obligatorios que NO se han usado en este paper.
        """
        mandatory_tags = self.extraction_phase.tags.mandatory()
        used_tag_ids = self.quotes.values_list('tags__id', flat=True).distinct()
        return mandatory_tags.exclude(id__in=used_tag_ids)
    
    def get_used_mandatory_tags(self):
        """
        Tags obligatorios que SÍ se han usado en este paper.
        """
        mandatory_tags = self.extraction_phase.tags.mandatory()
        used_tag_ids = self.quotes.values_list('tags__id', flat=True).distinct()
        return mandatory_tags.filter(id__in=used_tag_ids)
    
    def get_coverage_percentage(self):
        """
        Porcentaje de tags obligatorios cubiertos (0-100).
        """
        mandatory_tags = self.extraction_phase.tags.mandatory()
        
        if not mandatory_tags.exists():
            return 100
        
        used_count = self.get_used_mandatory_tags().count()
        total_count = mandatory_tags.count()
        
        return int((used_count / total_count) * 100)

    def is_complete_compliant(self):
        """
        Retorna True si todos los tags obligatorios han sido cubiertos.
        """
        return not self.get_missing_mandatory_tags().exists()

    class Meta:
        verbose_name = "Extracción de Paper"
        verbose_name_plural = "Extracciones de Papers"
        unique_together = ('study', 'extraction_phase')

    def __str__(self):
        return f"Extracción de {self.study.title} en {self.extraction_phase.project.title}"


class Quote(AuditModel):
    """Extracciones de texto (citas) de un documento (PaperExtraction)."""

    text_fragment = models.TextField(verbose_name="Fragmento de Texto Extraído", null=True, blank=True)
    # Usa JSONField para almacenar la ubicación estructurada
    location = models.JSONField(
        default=dict,
        verbose_name="Ubicación (Página, Párrafo, etc.)"
    )
    paper_extraction = models.ForeignKey(
        PaperExtraction,
        on_delete=models.CASCADE,
        related_name='quotes',
        verbose_name="Paper de Origen",
        null=True,
    )
    tags = models.ManyToManyField(
        'extraction.Tag',
        related_name='quotes',
        verbose_name="Etiquetas Aplicadas"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_quotes',
        verbose_name="Creado Por"
    )

    class Meta:
        verbose_name = "Cita de Extracción"
        verbose_name_plural = "Citas de Extracción"
        ordering = ['created_at']

    def __str__(self):
        return f"Cita de '{self.text_fragment[:50]}...' de {self.paper_extraction.study.title}"