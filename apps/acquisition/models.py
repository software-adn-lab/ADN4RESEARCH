"""
Django ORM Models for Acquisition module.

IMPORTANTE: Estos modelos son INFRAESTRUCTURA, no dominio.
La lógica de negocio vive en apps/acquisition/shared/domain/entities/study.py

El Repository (DjangoStudyRepository) se encarga de mapear:
- Modelo Django → Entidad de Dominio (para leer)
- Entidad de Dominio → Modelo Django (para escribir)
"""

from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid


class StudyModel(models.Model):
    """
    Modelo Django ORM para persistir estudios académicos.

    NOTA: Este es el modelo de PERSISTENCIA, no el modelo de DOMINIO.
    El modelo de dominio (Study) está en shared/domain/entities/study.py
    """

    # Identificación
    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Identificador único del estudio (UUID)"
    )
    title = models.TextField(
        help_text="Título del estudio"
    )
    link = models.URLField(
        max_length=500,
        help_text="URL al estudio en la fuente original"
    )
    source = models.CharField(
        max_length=100,
        help_text="Fuente académica (Scopus, IEEE Xplore, etc.)"
    )
    doi = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        db_index=True,
        help_text="Digital Object Identifier"
    )
    status = models.CharField(
        max_length=20,
        default="discovered",
        db_index=True,
        help_text="Estado del estudio en el workflow (discovered, enriched, downloaded, failed)"
    )

    # Metadata (Feature 3)
    authors = ArrayField(
        models.CharField(max_length=200),
        null=True,
        blank=True,
        help_text="Lista de autores"
    )
    abstract = models.TextField(
        null=True,
        blank=True,
        help_text="Resumen del estudio"
    )
    year = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Año de publicación"
    )
    journal = models.CharField(
        max_length=300,
        null=True,
        blank=True,
        help_text="Nombre de la revista/conferencia"
    )
    keywords = ArrayField(
        models.CharField(max_length=100),
        null=True,
        blank=True,
        help_text="Palabras clave"
    )

    # Texto completo (Feature 4)
    pdf_path = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Ruta al archivo PDF descargado"
    )
    pdf_source = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Fuente desde donde se obtuvo el PDF"
    )
    download_status = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Estado de disponibilidad del PDF (texto_completo_disponible, no_disponible, pendiente)"
    )

    # Consolidación de metadatos (Feature 3)
    consolidation_status = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Estado de calidad de metadatos (completo, parcial, fallido)"
    )
    field_origins = models.JSONField(
        default=dict,
        blank=True,
        help_text="Trazabilidad de origen de cada campo (ej: {'doi': 'manual', 'title': 'discovery'})"
    )

    # Auditoría
    discovered_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp de cuándo se descubrió el estudio"
    )
    enriched_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp de cuándo se enriquecieron los metadatos"
    )
    downloaded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp de cuándo se descargó el PDF"
    )
    failure_reason = models.TextField(
        null=True,
        blank=True,
        help_text="Razón de fallo si status=failed"
    )

    # Meta Django
    class Meta:
        db_table = "acquisition_study"
        verbose_name = "Study"
        verbose_name_plural = "Studies"
        ordering = ["-discovered_at"]
        indexes = [
            models.Index(fields=["doi"]),
            models.Index(fields=["status"]),
            models.Index(fields=["year"]),
            models.Index(fields=["source", "title"]),  # Para deduplicación rápida
        ]

    def __str__(self):
        return f"Study({self.uuid}): {self.title[:50]}..."
