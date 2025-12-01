from django.db import models
from django.conf import settings
from django.utils import timezone

# ==============================================================================
# 1. QUERYSET PERSONALIZADO (Lo que tu amigo necesita para que sus Vistas no fallen)
# ==============================================================================
class SearchStrategyQuerySet(models.QuerySet):
    def by_project(self, project_id):
        """Filtra estrategias por proyecto (Vital para el Frontend de Diseño)"""
        return self.filter(research_question__design_phase_id=project_id)

    def active(self):
        """
        Retorna estrategias que no están archivadas.
        NOTA PARA TU AMIGO: Antes usábamos status='ACTIVE', ahora 'active' significa
        todo lo que no sea 'ARCHIVED' o 'DRAFT' inicial.
        """
        return self.exclude(status__in=[
            SearchStrategy.Status.ARCHIVED, 
            SearchStrategy.Status.DRAFT
        ])

    def ready_for_execution(self):
        """Filtro para el orquestador"""
        return self.filter(status__in=[
            SearchStrategy.Status.READY, 
            SearchStrategy.Status.TESTING, 
            SearchStrategy.Status.FINAL
        ])

# ==============================================================================
# 2. MODELO PRINCIPAL (La Fuente de Verdad Unificada)
# ==============================================================================
class SearchStrategy(models.Model):
    """
    MODELO UNIFICADO: Gestiona el ciclo de vida completo.
    - Design: Define qué buscar.
    - Acquisition: Ejecuta y reporta resultados.
    """
    
    class Status(models.TextChoices):
        # --- Estados de Diseño (Lo que tu amigo maneja) ---
        DRAFT = 'DRAFT', 'Draft - Building strategy'
        READY = 'READY', 'Ready for execution'          # Reemplaza al antiguo ACTIVE
        TESTING = 'TESTING', 'Currently testing'        # Nuevo: Para pruebas piloto
        FINAL = 'FINAL', 'Final version'                # Nuevo: Versión congelada
        # --- Estados de Adquisición (Lo que tu módulo reporta) ---
        EXECUTING = 'EXECUTING', 'Currently executing'
        COMPLETED = 'COMPLETED', 'Execution completed'
        FAILED = 'FAILED', 'Execution failed'
        # --- Estados Comunes ---
        ARCHIVED = 'ARCHIVED', 'Archived'

    # --- Relaciones ---
    research_question = models.ForeignKey(
        'design.ResearchQuestion',
        on_delete=models.CASCADE,
        related_name='search_strategies'
    )
    
    # --- Datos Básicos ---
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    
    # --- INPUT (Responsabilidad de Diseño) ---
    # La cadena legible por humanos (ej: "Machine Learning AND Java")
    # Tu amigo usa este campo para mostrarlo en el UI.
    final_search_string = models.TextField(blank=True)
    
    # --- INPUT TÉCNICO (Responsabilidad de Adquisición - NUEVO) ---
    # La estructura exacta (JSON) que usan los robots. 
    # Tu amigo puede ignorar este campo, es para el backend.
    definition = models.JSONField(
        default=dict,
        blank=True,
        help_text="Definición normalizada (JSON) usada para la ejecución"
    )

    # --- FEEDBACK / ESTADÍSTICAS (NUEVO - Valor agregado para Diseño) ---
    # Estos campos sirven para que Diseño muestre: "Se encontraron 50 papers".
    total_executions = models.PositiveIntegerField(default=0)
    total_studies_found = models.PositiveIntegerField(default=0)
    total_new_studies = models.PositiveIntegerField(default=0)

    # --- AUDITORÍA (NUEVO) ---
    last_executed_at = models.DateTimeField(null=True, blank=True)
    last_executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='executed_search_strategies'
    )
    final_execution_id = models.UUIDField(null=True, blank=True)

    # --- AUDITORÍA DE CREACIÓN ---
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_search_strategies'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # CONECTAMOS EL QUERYSET AQUÍ (Esto arregla lo de tu amigo)
    objects = SearchStrategyQuerySet.as_manager()

    class Meta:
        db_table = "design_search_strategy"
        verbose_name = "Search Strategy"
        verbose_name_plural = "Search Strategies"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["research_question", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    # === MÉTODOS DE NEGOCIO (Rich Model) ===

    def mark_as_ready_for_testing(self):
        """Design: Marca lista para pruebas piloto"""
        self.status = self.Status.READY
        self.save(update_fields=['status'])

    def mark_as_final(self, final_execution_id=None):
        """Design: Congela la estrategia como versión definitiva"""
        self.status = self.Status.FINAL
        if final_execution_id:
            self.final_execution_id = final_execution_id
        self.save(update_fields=['status', 'final_execution_id'])

    def start_execution(self, user):
        """Acquisition: Inicia proceso de búsqueda"""
        self.status = self.Status.EXECUTING
        self.last_executed_by = user
        self.last_executed_at = timezone.now()
        self.save(update_fields=['status', 'last_executed_by', 'last_executed_at'])

    def complete_execution(self, studies_found, new_studies):
        """Acquisition: Finaliza con éxito y actualiza stats"""
        self.status = self.Status.COMPLETED
        self.total_executions += 1
        self.total_studies_found = studies_found 
        self.total_new_studies = new_studies
        self.save(update_fields=[
            'status', 'total_executions', 
            'total_studies_found', 'total_new_studies'
        ])

    def fail_execution(self):
        """Acquisition: Marca error en el proceso"""
        self.status = self.Status.FAILED
        self.total_executions += 1
        self.save(update_fields=['status', 'total_executions'])

    def is_final(self):
        return self.status == self.Status.FINAL

    def __str__(self):
        return f"Strategy '{self.name}' ({self.get_status_display()})"


# ==============================================================================
# 3. VERSIONAMIENTO (Se mantiene igual, no rompe nada)
# ==============================================================================
class SearchStrategyVersion(models.Model):
    strategy = models.ForeignKey(
        SearchStrategy,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    version_number = models.PositiveIntegerField()
    final_search_string = models.TextField()
    
    metadata_snapshot = models.JSONField(default=dict) 
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True
    )

    class Meta:
        ordering = ['-version_number']
        unique_together = ('strategy', 'version_number')

    def __str__(self):
        return f"v{self.version_number} of Strategy {self.strategy_id}"