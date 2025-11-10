from django.db import models


class SubTheme(models.Model):
    """
    Representa un subtema dentro de un tema principal.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pendiente'
        IN_PROGRESS = 'IN_PROGRESS', 'En Progreso'
        INTERPRETATION_COMPLETED = 'INTERPRETATION_COMPLETED', 'Interpretación Finalizada'

    theme = models.ForeignKey(
        'interpretation.Theme',
        on_delete=models.CASCADE,
        related_name='subthemes'
    )
    name = models.CharField(max_length=255)
    central_codes = models.JSONField(default=list, blank=True)  # Lista de códigos centrales
    key_citations = models.JSONField(default=list, blank=True)  # Citas clave de estudios
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SubTheme: {self.name} ({self.theme.name})"
