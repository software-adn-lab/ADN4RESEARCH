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

    def can_be_completed(self) -> tuple[bool, str]:
        """
        Verifica si el paper puede ser marcado como completado.
        
        Business Rules:
        - Debe tener al menos una quote
        - Todas las tags obligatorias deben estar cubiertas
        
        Returns:
            tuple[bool, str]: (puede_completarse, mensaje_error)
        """
        # 1. Verificar que tenga quotes
        if not self.quotes.exists():
            return False, "El paper debe tener al menos una extracción (quote)."
        
        # 2. Verificar cobertura de tags obligatorios
        missing_tags = self.get_missing_mandatory_tags()
        if missing_tags.exists():
            tag_names = ", ".join([tag.name for tag in missing_tags[:3]])
            if missing_tags.count() > 3:
                tag_names += f" (+{missing_tags.count() - 3} más)"
            return False, f"Faltan tags obligatorios: {tag_names}"
        
        return True, ""

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
    
    def get_all_used_tags(self):
        """
        Todos los tags (obligatorios y opcionales) usados en este paper.
        """
        from apps.extraction.taxonomy.models import Tag
        return Tag.objects.filter(
            quotes__paper_extraction=self
        ).distinct()
    
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
    
    def mark_as_completed(self):
        """
        Marca el paper como completado.
        
        Raises:
            BusinessRuleViolation: Si no cumple las reglas
        """
        from apps.extraction.shared.exceptions import BusinessRuleViolation
        
        can_complete, error_message = self.can_be_completed()
        
        if not can_complete:
            raise BusinessRuleViolation(error_message)
        
        self.status = PaperExtractionStatusChoices.COMPLETED
        self.save(update_fields=['status', 'updated_at'])

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