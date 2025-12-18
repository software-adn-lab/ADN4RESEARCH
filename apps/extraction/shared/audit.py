from django.db import models

class AuditModel(models.Model):
    """Modelo abstracto para añadir campos de auditoría."""
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")

    class Meta:
        abstract = True