from django.db import models
from django.utils.translation import gettext_lazy as _


class Tag(models.Model):
    """
    Entidad Tag.
    No tiene FK a ResearchQuestion, solo guarda el ID de referencia.
    """
    class TagType(models.TextChoices):
        DEDUCTIVE = 'deductive', _('Deductivo')
        INDUCTIVE = 'inductive', _('Inductivo')

    class ApprovalStatus(models.TextChoices):
        PENDING = 'pending', _('Pendiente de Aprobación')
        APPROVED = 'approved', _('Aprobado')
        REJECTED = 'rejected', _('Rechazado')

    name = models.CharField(max_length=100)
    color = models.CharField(max_length=50, default='#FFFFFF')
    justification = models.TextField(blank=True)
    
    # Referencia débil a Identity Management (Users)
    # También sirve como owner_id para tags inductivos privados
    created_by_id = models.IntegerField(null=True, db_index=True)
    
    # Referencia débil al Bounded Context 'Design'
    question_id = models.IntegerField(
        null=True, 
        blank=True, 
        db_index=True,
        help_text="ID de la ResearchQuestion externa"
    )
    
    # Contexto del proyecto (Multi-tenancy lógico)
    project_id = models.IntegerField(db_index=True)

    type = models.CharField(
        max_length=20, 
        choices=TagType.choices, 
        default=TagType.DEDUCTIVE
    )
    
    # Estado de aprobación para tags inductivos
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.APPROVED
    )
    
    is_mandatory = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Para fusión de tags duplicados
    merged_into = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='merged_from'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'project_id', 'question_id'],
                name='unique_tag_per_context'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"
    
    @property
    def is_active(self) -> bool:
        """Un tag está activo si no ha sido fusionado en otro"""
        return self.merged_into is None
    
    @property
    def is_visible_to_all(self) -> bool:
        """Visible para todos si es público y está aprobado"""
        return self.is_public and self.approval_status == self.ApprovalStatus.APPROVED
