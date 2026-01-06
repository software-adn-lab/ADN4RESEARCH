from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator

from ..shared.audit import AuditModel


User = get_user_model()

class TagQuerySet(models.QuerySet):
    """
    Reemplaza a TagRepository. Encapsula lógica de filtrado.
    """
    def mandatory(self):
        return self.filter(is_mandatory=True)

    def deductives(self):
        return self.filter(type='DEDUCTIVE')

    def visible_for(self, user):
        """Regla de negocio: Tags públicos O tags propios del usuario."""
        return self.filter(
            Q(visibility='PUBLIC') | Q(created_by=user)
        )


class TagTypeChoices:
    """Opciones para el tipo de Tag."""
    DEDUCTIVE = 'DEDUCTIVE'
    INDUCTIVE = 'INDUCTIVE'

    CHOICES = [
        (DEDUCTIVE, 'Deductiva'),
        (INDUCTIVE, 'Inductiva'),
    ]

class ApprovalStatusChoices:
    """Opciones para el estado de aprobación/revisión (usado en Tag y posiblemente otros)."""
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'

    CHOICES = [
        (PENDING, 'Pendiente'),
        (APPROVED, 'Aprobada'),
        (REJECTED, 'Rechazada'),
    ]


class VisibilityChoices:
    """Opciones para la visibilidad (usado en Tag)."""
    PUBLIC = 'PUBLIC'
    PRIVATE = 'PRIVATE'

    CHOICES = [
        (PUBLIC, 'Pública'),
        (PRIVATE, 'Privada'),
    ]


class Tag(AuditModel):
    """Etiquetas que se pueden agregar a una extracción de texto (Quote)."""

    hex_validator = RegexValidator(
        regex=r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$',
        message="El color debe ser un código hexadecimal válido (e.g., #FF00AA)."
    )

    name = models.CharField(max_length=100, verbose_name="Nombre de la Etiqueta", null=True, blank=True)
    color = models.CharField(
        max_length=7,
        validators=[hex_validator],
        verbose_name="Color Hexadecimal",
        null=True,
        blank=True
    )
    extraction_phase = models.ForeignKey(
        'extraction.ExtractionPhase',
        on_delete=models.CASCADE,
        related_name='tags',
        verbose_name="Fase de Extracción",
        null=True
    )
    rq_related = models.ForeignKey(
        'design.ResearchQuestion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tags',
        verbose_name="Pregunta de Investigación Relacionada",
        db_column='question_id'
    )
    is_mandatory = models.BooleanField(
        default=False,
        verbose_name="Es Obligatoria"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tags',
        verbose_name="Creado Por"
    )
    type = models.CharField(
        max_length=10,
        choices=TagTypeChoices.CHOICES,
        default=TagTypeChoices.DEDUCTIVE,
        verbose_name="Tipo de Etiqueta"
    )
    status = models.CharField(
        max_length=10,
        choices=ApprovalStatusChoices.CHOICES,
        default=ApprovalStatusChoices.PENDING,
        verbose_name="Estado de Aprobación"
    )
    visibility = models.CharField(
        max_length=10,
        choices=VisibilityChoices.CHOICES,
        default=VisibilityChoices.PUBLIC,
        verbose_name="Visibilidad"
    )

    objects = TagQuerySet.as_manager()

    class Meta:
        unique_together = ('extraction_phase', 'name')

    def __str__(self):
        return f"Tag: {self.name}"