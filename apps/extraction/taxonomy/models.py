"""
Bounded Context: Taxonomy
Modelos relacionados con el sistema de etiquetado (Tags)

Referencia Django ORM:
https://docs.djangoproject.com/en/stable/topics/db/models/
https://docs.djangoproject.com/en/stable/ref/models/querysets/
"""
from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.core.exceptions import PermissionDenied

from ..shared.audit import AuditModel


User = get_user_model()


class TagTypeChoices:
    """Opciones para el tipo de Tag."""
    DEDUCTIVE = 'DEDUCTIVE'
    INDUCTIVE = 'INDUCTIVE'

    CHOICES = [
        (DEDUCTIVE, 'Deductiva'),
        (INDUCTIVE, 'Inductiva'),
    ]


class ApprovalStatusChoices:
    """Opciones para el estado de aprobación."""
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'

    CHOICES = [
        (PENDING, 'Pendiente'),
        (APPROVED, 'Aprobada'),
        (REJECTED, 'Rechazada'),
    ]


class VisibilityChoices:
    """Opciones para la visibilidad."""
    PUBLIC = 'PUBLIC'
    PRIVATE = 'PRIVATE'

    CHOICES = [
        (PUBLIC, 'Pública'),
        (PRIVATE, 'Privada'),
    ]


class TagQuerySet(models.QuerySet):
    """
    QuerySet personalizado que encapsula lógica de filtrado de Tags.
    
    Referencia:
    https://docs.djangoproject.com/en/stable/ref/models/querysets/#django.db.models.query.QuerySet
    """
    
    def mandatory(self):
        """Tags marcados como obligatorios."""
        return self.filter(
            Q(is_mandatory=True) | Q(rq_related__isnull=False),
            status=ApprovalStatusChoices.APPROVED,
            type=TagTypeChoices.DEDUCTIVE
        )

    def deductives(self):
        """Tags de tipo deductivo."""
        return self.filter(type=TagTypeChoices.DEDUCTIVE)
    
    def inductives(self):
        """Tags de tipo inductivo."""
        return self.filter(type=TagTypeChoices.INDUCTIVE)
    
    def pending_approval(self):
        """Tags inductivos pendientes de aprobación."""
        return self.filter(
            type=TagTypeChoices.INDUCTIVE,
            status=ApprovalStatusChoices.PENDING
        )
    
    def approved(self):
        """Tags aprobados (tanto deductivos como inductivos)."""
        return self.filter(status=ApprovalStatusChoices.APPROVED)

    def visible_for(self, user):
        """
        Regla de negocio: Tags que un usuario puede VER.
        - Tags públicos (aprobados)
        - Tags privados propios del usuario (pendientes inductivos)
        """
        return self.filter(
            Q(visibility=VisibilityChoices.PUBLIC) | 
            Q(created_by=user, visibility=VisibilityChoices.PRIVATE)
        )
    
    def usable_by(self, user):
        """
        Regla de negocio: Tags que un usuario puede USAR en una Quote.
        - Tags deductivos aprobados (públicos)
        - Tags inductivos aprobados (públicos)
        - Tags inductivos pendientes propios del usuario
        """
        return self.filter(
            # Tags aprobados (públicos) - deductivos e inductivos
            Q(status=ApprovalStatusChoices.APPROVED, visibility=VisibilityChoices.PUBLIC) |
            # Tags inductivos pendientes propios
            Q(
                type=TagTypeChoices.INDUCTIVE,
                status=ApprovalStatusChoices.PENDING,
                created_by=user
            )
        )
    
    def for_phase(self, phase_id):
        """Tags de una fase de extracción específica."""
        return self.filter(extraction_phase_id=phase_id)


class Tag(AuditModel):
    """
    Etiquetas que se pueden agregar a una extracción de texto (Quote).
    
    Tipos de Tags:
    - DEDUCTIVE: Definidos a priori por el líder del proyecto. Públicos desde creación.
    - INDUCTIVE: Emergen durante la extracción. Privados hasta aprobación.
    
    Referencia:
    https://docs.djangoproject.com/en/stable/topics/db/models/
    """

    hex_validator = RegexValidator(
        regex=r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$',
        message="El color debe ser un código hexadecimal válido (e.g., #FF00AA)."
    )

    name = models.CharField(
        max_length=100, 
        verbose_name="Nombre de la Etiqueta", 
        null=True, 
        blank=True
    )
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
        verbose_name="Pregunta de Investigación Relacionada"
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
        verbose_name = "Etiqueta"
        verbose_name_plural = "Etiquetas"
        ordering = ['name']

    def __str__(self):
        return f"Tag: {self.name} ({self.get_type_display()})"
    
    # =====================
    # Propiedades de estado
    # =====================
    
    @property
    def is_inductive(self) -> bool:
        """Indica si el tag es de tipo inductivo."""
        return self.type == TagTypeChoices.INDUCTIVE
    
    @property
    def is_deductive(self) -> bool:
        """Indica si el tag es de tipo deductivo."""
        return self.type == TagTypeChoices.DEDUCTIVE
    
    @property
    def is_pending(self) -> bool:
        """Indica si el tag está pendiente de aprobación."""
        return self.status == ApprovalStatusChoices.PENDING
    
    @property
    def is_approved(self) -> bool:
        """Indica si el tag está aprobado."""
        return self.status == ApprovalStatusChoices.APPROVED
    
    @property
    def is_private(self) -> bool:
        """Indica si el tag es privado."""
        return self.visibility == VisibilityChoices.PRIVATE
    
    @property
    def is_public(self) -> bool:
        """Indica si el tag es público."""
        return self.visibility == VisibilityChoices.PUBLIC
    
    # =====================
    # Métodos de dominio
    # =====================
    
    def can_be_used_by(self, user) -> bool:
        """
        Determina si un usuario puede usar este tag.
        
        Reglas:
        - Tags aprobados: cualquier usuario del proyecto
        - Tags inductivos pendientes: solo el creador
        """
        if self.is_approved:
            return True
        
        if self.is_inductive and self.is_pending:
            return self.created_by == user
        
        return False
    
    def can_be_approved_by(self, user) -> bool:
        """
        Determina si un usuario puede aprobar este tag.
        Solo tags inductivos pendientes pueden ser aprobados.
        
        Nota: La lógica de permisos (ej. es líder del proyecto) 
        debe validarse en la capa de vista/servicio.
        """
        return self.is_inductive and self.is_pending
    
    def approve(self, approved_by=None):
        """
        Aprueba un tag inductivo.
        
        Al aprobar:
        - Estado cambia a APPROVED
        - Visibilidad cambia a PUBLIC
        
        Args:
            approved_by: Usuario que aprueba (opcional, para auditoría)
        
        Raises:
            ValueError: Si el tag no puede ser aprobado
        """
        if not self.can_be_approved_by(approved_by):
            raise ValueError(
                f"El tag '{self.name}' no puede ser aprobado. "
                f"Estado actual: {self.get_status_display()}, "
                f"Tipo: {self.get_type_display()}"
            )
        
        self.status = ApprovalStatusChoices.APPROVED
        self.visibility = VisibilityChoices.PUBLIC
        self.save(update_fields=['status', 'visibility', 'updated_at'])
    
    def reject(self, rejected_by=None, reason: str = None):
        """
        Rechaza un tag inductivo.
        
        Args:
            rejected_by: Usuario que rechaza (opcional, para auditoría)
            reason: Motivo del rechazo (opcional)
        
        Raises:
            ValueError: Si el tag no puede ser rechazado
        """
        if not (self.is_inductive and self.is_pending):
            raise ValueError(
                f"El tag '{self.name}' no puede ser rechazado. "
                f"Solo tags inductivos pendientes pueden rechazarse."
            )
        
        self.status = ApprovalStatusChoices.REJECTED
        self.save(update_fields=['status', 'updated_at'])
