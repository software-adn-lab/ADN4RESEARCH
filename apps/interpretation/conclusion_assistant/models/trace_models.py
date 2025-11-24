"""Models for analysis traceability and methodological reflexivity."""
from django.db import models
from django.conf import settings


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
        try:
            trace_label = self.TraceType(self.trace_type).label
        except Exception:
            trace_label = self.trace_type or ''
        return f"{trace_label} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
