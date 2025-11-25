from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from django.utils import timezone

from ..domain.value_objects.extraction_mode import ExtractionMode
from ..domain.value_objects.extraction_status import ExtractionStatus
from ..domain.value_objects.phase_status import PhaseStatus
from ..domain.value_objects.tag_status import TagStatus
from ..domain.value_objects.tag_type import TagType
from ..domain.value_objects.tag_visibility import TagVisibility


class ExtractionPhaseModel(models.Model):
    """
    Configuración de la fase de extracción para un Proyecto específico.

    Reglas de Negocio:
    - Solo puede haber una fase por proyecto (OneToOne)
    - Si auto_close=True, se cierra automáticamente al alcanzar end_date
    - El modo determina cuántas extracciones se permiten por estudio
    """

    project_id = models.IntegerField(
        unique=True,  # ✅ Garantiza una sola fase por proyecto
        help_text="ID del proyecto en el servicio de Projects",
        db_index=True
    )

    mode = models.CharField(
        max_length=20,
        choices=[(m.value, m.value) for m in ExtractionMode],
        default=ExtractionMode.SINGLE.value,
        help_text="Modo de extracción: simple, doble o triple"
    )

    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.value) for s in PhaseStatus],
        default=PhaseStatus.INACTIVE.value
    )

    start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha de inicio de la fase"
    )

    end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha de cierre de la fase"
    )

    auto_close = models.BooleanField(
        default=False,
        help_text="Cerrar automáticamente al llegar a end_date"
    )

    allow_late_submissions = models.BooleanField(
        default=False,
        help_text="Permitir extracciones después de end_date"
    )

    min_quotes_required = models.PositiveIntegerField(
        default=1,
        help_text="Mínimo de quotes requeridas por extracción"
    )

    max_quotes_per_extraction = models.PositiveIntegerField(
        default=100,
        help_text="Máximo de quotes por extracción"
    )

    requires_approval = models.BooleanField(
        default=False,
        help_text="Las extracciones completadas requieren aprobación del owner"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'extraction_phase'
        verbose_name = "Extraction Phase"
        verbose_name_plural = "Extraction Phases"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project_id', 'status']),
            models.Index(fields=['status', 'end_date']),  # Para auto_close jobs
        ]

    def __str__(self):
        return f"Extraction Phase - Project {self.project_id} ({self.status})"

    def clean(self):
        """Validaciones a nivel de modelo"""
        if self.end_date and self.start_date:
            if self.end_date <= self.start_date:
                raise ValidationError(
                    "La fecha de fin debe ser posterior a la fecha de inicio"
                )

        if self.min_quotes_required > self.max_quotes_per_extraction:
            raise ValidationError(
                "El mínimo de quotes no puede ser mayor al máximo"
            )

class ExtractionModel(models.Model):
    """Modelo de persistencia para la entidad Extraction."""
    study_id = models.BigIntegerField(
        help_text="ID del estudio en el servicio de Acquisition/Studies",
        db_index=True
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='extractions'
    )
    status = models.CharField(
        max_length=20,
        choices=[(tag.value, tag.value) for tag in ExtractionStatus],
        default=ExtractionStatus.PENDING
    )
    extraction_order = models.PositiveSmallIntegerField(
        default=1,
        help_text="Orden de extracción (1=primera, 2=segunda en double extraction)"
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'extraction_extraction'
        indexes = [
            models.Index(fields=['study_id', 'assigned_to']),
            models.Index(fields=['study_id', 'extraction_order']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['study_id', 'assigned_to'],
                name='unique_study_user_extraction'
            )
        ]

    def __str__(self):
        return f"Extraction {self.id} - Study {self.study_id} (Order: {self.extraction_order})"
    

class TagModel(models.Model):
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=20, default="#FFFFFF")
    type = models.CharField(
        max_length=20,
        choices=[(t.value, t.value) for t in TagType],
        default=TagType.DEDUCTIVE
    )
    is_mandatory = models.BooleanField(default=False)
    question_id = models.IntegerField(null=True, blank=True)
    project_id = models.IntegerField(help_text="Project context ID")
    created_by_user_id = models.IntegerField(help_text="User ID")
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.value) for s in TagStatus],
        default=TagStatus.PENDING.value
    )
    visibility = models.CharField(
        max_length=20,
        choices=[(s.value, s.value) for s in TagVisibility],
        default=TagVisibility.PRIVATE.value
    )

    class Meta:
        db_table = 'extraction_tag'

class QuoteModel(models.Model):
    extraction = models.ForeignKey(
        ExtractionModel,
        on_delete=models.CASCADE,
        related_name='quotes'
    )
    text_portion = models.TextField()
    location_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Ubicación estructurada: {page, text_location, coordinates}"
    )
    researcher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    tags = models.ManyToManyField(TagModel, related_name='quotes', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'extraction_quote'
        indexes = [
            models.Index(fields=['extraction', 'created_at']),
        ]

    def __str__(self):
        page_info = ""
        if self.location_data and self.location_data.get('page'):
            page_info = f" (Pág. {self.location_data['page']})"
        return f"Quote {self.id}{page_info}: {self.text_portion[:50]}"