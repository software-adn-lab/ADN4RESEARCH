"""
Django ORM Models for Acquisition module.

IMPORTANTE: Estos modelos son INFRAESTRUCTURA, no dominio.
La lógica de negocio vive en apps/acquisition/shared/domain/entities/study.py

El Repository (DjangoStudyRepository) se encarga de mapear:
- Modelo Django → Entidad de Dominio (para leer)
- Entidad de Dominio → Modelo Django (para escribir)

Estructura de persistencia:
1. SearchStrategyModel: Guarda la definición de búsqueda (NormalizedStrategy)
2. SearchExecutionModel: Guarda cada ejecución de búsqueda (auditoría)
3. StudyModel: Guarda los papers descubiertos
4. ExecutionStudy: Relación M2M entre ejecuciones y estudios (con metadata)
"""

from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.conf import settings
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


# ==============================================================================
# MODELOS DE TRAZABILIDAD Y AUDITORÍA
# ==============================================================================


class SearchStrategyModel(models.Model):
    """
    Modelo Django para persistir estrategias de búsqueda.

    Guarda la definición de búsqueda (NormalizedStrategy) que se usará
    para ejecutar búsquedas en proveedores académicos.

    Integración con Design:
    - Vinculado a ResearchQuestion del módulo Design
    - Permite reproducibilidad y trazabilidad de búsquedas
    """

    # Identificación
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Identificador único de la estrategia"
    )

    # INTEGRACIÓN CON DESIGN: Vinculación a pregunta de investigación
    research_question = models.ForeignKey(
        'design.ResearchQuestion',
        on_delete=models.CASCADE,
        related_name='search_strategies',
        null=True,
        blank=True,
        help_text="Pregunta de investigación asociada (módulo Design)"
    )

    # Definición de búsqueda (JSON de NormalizedStrategy)
    # Ejemplo: {"strategy_id": "...", "main_terms": [...], "exclusions": [...], "filters": {...}}
    definition = models.JSONField(
        help_text="Definición de la estrategia de búsqueda (NormalizedStrategy serializada)"
    )

    # Metadata descriptiva
    name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Nombre descriptivo de la estrategia"
    )
    description = models.TextField(
        null=True,
        blank=True,
        help_text="Descripción detallada de la estrategia"
    )

    # Auditoría
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_search_strategies',
        help_text="Usuario que creó la estrategia"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de creación"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Última actualización"
    )

    class Meta:
        db_table = "acquisition_search_strategy"
        verbose_name = "Search Strategy"
        verbose_name_plural = "Search Strategies"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["research_question", "-created_at"]),
        ]

    def __str__(self):
        name_part = self.name or "Unnamed"
        return f"Strategy({self.id}): {name_part}"


class SearchExecutionModel(models.Model):
    """
    Modelo Django para registrar ejecuciones de búsqueda.

    Guarda auditoría de CUÁNDO se ejecutó una estrategia,
    QUÉ queries exactas se usaron, y QUÉ resultados se obtuvieron.
    """

    # Identificación
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Identificador único de la ejecución"
    )

    # Vinculación a estrategia
    strategy = models.ForeignKey(
        SearchStrategyModel,
        on_delete=models.CASCADE,
        related_name='executions',
        help_text="Estrategia que se ejecutó"
    )

    # Auditoría de ejecución
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='executed_searches',
        help_text="Usuario que ejecutó la búsqueda"
    )
    executed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp de ejecución"
    )

    # Trazas de traducción (Output del TranslationService)
    # Ejemplo: {"queries_by_source": {"Scopus": "TITLE-ABS-KEY(...)", "IEEE": "(...)"}}
    translated_queries = models.JSONField(
        default=dict,
        blank=True,
        help_text="Queries traducidas por proveedor (salida de TranslationService)"
    )

    # Estadísticas de resultados
    results_count = models.IntegerField(
        default=0,
        help_text="Número total de estudios encontrados en esta ejecución"
    )
    new_studies_count = models.IntegerField(
        default=0,
        help_text="Número de estudios nuevos (no duplicados)"
    )

    # Estado de la ejecución
    STATUS_CHOICES = [
        ('SUCCESS', 'Success'),
        ('PARTIAL', 'Partial Success'),
        ('FAILED', 'Failed'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='SUCCESS',
        help_text="Estado de la ejecución"
    )
    error_details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detalles de errores por proveedor si status != SUCCESS"
    )

    # Relación M2M con Studies (a través de ExecutionStudy)
    studies = models.ManyToManyField(
        StudyModel,
        through='ExecutionStudy',
        related_name='executions',
        help_text="Estudios encontrados en esta ejecución"
    )

    class Meta:
        db_table = "acquisition_search_execution"
        verbose_name = "Search Execution"
        verbose_name_plural = "Search Executions"
        ordering = ["-executed_at"]
        indexes = [
            models.Index(fields=["strategy", "-executed_at"]),
            models.Index(fields=["executed_by", "-executed_at"]),
        ]

    def __str__(self):
        return f"Execution({self.id}) - {self.executed_at.strftime('%Y-%m-%d %H:%M')} - {self.results_count} results"


class ExecutionStudy(models.Model):
    """
    Tabla intermedia M2M entre SearchExecutionModel y StudyModel.

    Guarda metadata adicional sobre cómo se descubrió cada estudio:
    - ¿Era nuevo o duplicado?
    - ¿De qué proveedores vino?
    - ¿Cuál fue su posición en los resultados?
    """

    # Identificación
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Relaciones
    execution = models.ForeignKey(
        SearchExecutionModel,
        on_delete=models.CASCADE,
        help_text="Ejecución de búsqueda"
    )
    study = models.ForeignKey(
        StudyModel,
        on_delete=models.CASCADE,
        help_text="Estudio encontrado"
    )

    # Metadata de descubrimiento
    is_new = models.BooleanField(
        default=True,
        help_text="True si este estudio es nuevo en esta ejecución (no duplicado)"
    )
    providers = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
        help_text="Lista de proveedores que retornaron este estudio en esta ejecución"
    )
    rank_position = models.IntegerField(
        null=True,
        blank=True,
        help_text="Posición en resultados (para análisis de relevancia)"
    )

    # Auditoría
    linked_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Cuándo se vinculó este estudio a la ejecución"
    )

    class Meta:
        db_table = "acquisition_execution_study"
        verbose_name = "Execution-Study Link"
        verbose_name_plural = "Execution-Study Links"
        unique_together = [('execution', 'study')]
        indexes = [
            models.Index(fields=["execution", "is_new"]),
            models.Index(fields=["study"]),
        ]

    def __str__(self):
        new_flag = "NEW" if self.is_new else "DUP"
        return f"[{new_flag}] {self.execution.id} → {self.study.uuid}"
