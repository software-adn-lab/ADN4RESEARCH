from django.db import models


class InterpretationContext(models.Model):
    """
    Representa el contexto activo de una sesión de interpretación.
    """
    subtheme = models.OneToOneField(
        'interpretation.SubTheme',
        on_delete=models.CASCADE,
        related_name='context'
    )
    research_question = models.TextField()
    theme_name = models.CharField(max_length=255)
    extractions_context = models.JSONField(default=dict, blank=True)  # Datos de extracción relevantes
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Context for {self.subtheme.name}"
