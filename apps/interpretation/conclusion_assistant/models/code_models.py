"""Models for code normalization and theme discovery."""
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
        return f"{self.normalized_code} <- {', '.join(self.original_codes[:3])}"


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


class ThemeDiscoveryProposal(models.Model):
    """
    Representa una propuesta de estructura temática generada por IA.
    Agrupa códigos normalizados en temas y subtemas.
    """
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
        NormalizedCode,
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


class AnalysisTrace(models.Model):
    """
    Registra la traza del análisis por IA para fines de reflexividad y trazabilidad metodológica.
    Guarda las propuestas iniciales vs. las estructuras finales.
    """
    class TraceType(models.TextChoices):
        CODE_NORMALIZATION = 'CODE_NORMALIZATION', 'Normalización de Códigos'
        THEME_DISCOVERY = 'THEME_DISCOVERY', 'Descubrimiento de Temas'

    trace_type = models.CharField(
        max_length=30,
        choices=TraceType.choices
    )
    ai_proposal = models.JSONField(default=dict)  # Propuesta original de la IA
    researcher_modifications = models.JSONField(default=dict)  # Cambios del investigador
    final_result = models.JSONField(default=dict)  # Resultado final
    rationale = models.TextField(blank=True)  # Justificación del investigador
    project = models.ForeignKey(
        'project.Project',
        on_delete=models.CASCADE,
        related_name='analysis_traces',
        null=True,
        blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='analysis_traces'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Analysis Traces'

    def __str__(self):
        return f"{self.get_trace_type_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
