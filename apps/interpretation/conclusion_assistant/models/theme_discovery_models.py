"""Models for AI-driven theme discovery."""
from django.db import models
from django.conf import settings


class ThemeDiscoveryProposal(models.Model):
    """
    Representa una propuesta de estructura temática generada por IA.
    Agrupa códigos normalizados en temas y subtemas.
    """
    id: int  # Django auto-generated field
    
    class ProposalStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pendiente de Revisión'
        ACCEPTED = 'ACCEPTED', 'Aceptada'
        MODIFIED = 'MODIFIED', 'Modificada por el Investigador'
        REJECTED = 'REJECTED', 'Rechazada'

    theme_name = models.CharField(max_length=255)
    theme_description = models.TextField(blank=True)
    research_question_focus = models.CharField(max_length=100, blank=True)
    proposed_subthemes = models.JSONField(default=list)  # Lista de subtemas con sus códigos
    rationale = models.TextField(blank=True)  # Explicación de la IA
    status = models.CharField(
        max_length=20,
        choices=ProposalStatus.choices,
        default=ProposalStatus.PENDING
    )
    codes_used = models.ManyToManyField(
        'interpretation.NormalizedCode',
        related_name='theme_proposals'
    )
    project = models.ForeignKey(
        'project.Project',
        on_delete=models.CASCADE,
        related_name='theme_proposals',
        null=True,
        blank=True
    )
    created_by_ai = models.BooleanField(default=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_theme_proposals'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Theme Proposal: {self.theme_name} ({self.status})"
