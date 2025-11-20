"""Models for code normalization process."""
from django.db import models
from django.conf import settings


class InitialCode(models.Model):
    """
    Representa un código inicial (tag) extraído del Módulo de Extracción.
    Estos códigos son el punto de partida para la normalización.
    """
    code = models.CharField(max_length=255, unique=True)
    frequency = models.IntegerField(default=1)
    project = models.ForeignKey(
        'project.Project',
        on_delete=models.CASCADE,
        related_name='initial_codes',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-frequency', 'code']

    def __str__(self):
        return f"{self.code} (freq: {self.frequency})"


class CodeNormalizationProposal(models.Model):
    """
    Representa una propuesta de normalización de códigos generada por IA.
    Agrupa códigos similares y propone fusiones.
    """
    id: int  # Django auto-generated field

    class ProposalStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pendiente de Revisión'
        ACCEPTED = 'ACCEPTED', 'Aceptada por el Investigador'
        REJECTED = 'REJECTED', 'Rechazada'
        MODIFIED = 'MODIFIED', 'Modificada por el Investigador'

    normalized_code = models.CharField(max_length=255)
    original_codes = models.JSONField(default=list)  # Lista de códigos originales
    rationale = models.TextField(blank=True)  # Explicación de la IA sobre la fusión
    status = models.CharField(
        max_length=20,
        choices=ProposalStatus.choices,
        default=ProposalStatus.PENDING
    )
    project = models.ForeignKey(
        'project.Project',
        on_delete=models.CASCADE,
        related_name='normalization_proposals',
        null=True,
        blank=True
    )
    created_by_ai = models.BooleanField(default=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_normalizations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        codes = self.original_codes if isinstance(self.original_codes, list) else []
        return f"{self.normalized_code} <- {', '.join(codes[:3])}"


class NormalizedCode(models.Model):
    """
    Representa un código normalizado final, después de la revisión del investigador.
    Estos códigos se usan como base para la generación de temas.
    """
    code = models.CharField(max_length=255)
    original_codes = models.JSONField(default=list)  # Códigos que fueron fusionados
    research_question_focus = models.CharField(
        max_length=100,
        blank=True,
        help_text="RQ a la que responde este código (ej: RQ1, RQ2)"
    )
    frequency = models.IntegerField(default=1)
    proposal = models.ForeignKey(
        CodeNormalizationProposal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='normalized_codes'
    )
    project = models.ForeignKey(
        'project.Project',
        on_delete=models.CASCADE,
        related_name='normalized_codes',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['research_question_focus', '-frequency', 'code']

    def __str__(self):
        return f"{self.code} [{self.research_question_focus}]"
