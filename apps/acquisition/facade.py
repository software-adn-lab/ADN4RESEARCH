"""
AcquisitionFacade - Fachada limpia para comunicación entre módulos.

Esta fachada expone únicamente las operaciones que otros módulos
necesitan del módulo de Acquisition, ocultando toda la complejidad
interna de orquestación, traducción, descubrimiento y persistencia.

Responsabilidades:
- Proveer API simple para Design, Selection, Extraction
- Ocultar detalles de implementación de AcquisitionOrchestrator
- Mantener trazabilidad completa sin exponer complejidad
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from django.contrib.auth import get_user_model

# Fachada
from .shared.application.acquisition_orchestrator import (
    AcquisitionOrchestrator,
    SearchExecutionResult,
    EnrichmentResult,
)

# Dominio
from .shared.domain.entities.study import Study
from .translation.domain.models import NormalizedStrategy
from .shared.domain.constants import (
    normalize_source_names,
    DEFAULT_MAX_RESULTS_PER_SOURCE,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ==============================================================================
# DATA TRANSFER OBJECTS (DTOs) - Simplificados para otros módulos
# ==============================================================================


@dataclass
class PreviewSearchResult:
    """
    Resultado de una búsqueda en modo preview (sin persistir).

    Usado por Design para mostrar resultados antes de decidir qué guardar.
    
    Attributes:
        queries_by_source: Queries traducidas por fuente (ya filtradas por selected_sources)
        total_found: Total de estudios únicos (después de deduplicar)
        studies: Estudios como dicts simples (sin IDs de BD)
        strategy_dict: Estrategia original (para finalize)
        selected_sources: Fuentes que se consultaron (nombres canónicos)
        total_por_fuente: Cantidad de estudios retornados por fuente (limitado por max_results)
        total_available_by_source: Total REAL disponible en la API por fuente (None si no aplica)
    """
    queries_by_source: Dict[str, str]
    total_found: int
    studies: List[Dict[str, Any]]
    strategy_dict: Dict[str, Any]
    selected_sources: Optional[List[str]] = None  # Fuentes usadas (para trazabilidad)
    total_por_fuente: Optional[Dict[str, int]] = None  # Cantidad limitada por fuente
    total_available_by_source: Optional[Dict[str, Optional[int]]] = None  # Total real en API
    
    def __post_init__(self):
        if self.selected_sources is None:
            self.selected_sources = list(self.queries_by_source.keys())
        if self.total_por_fuente is None:
            self.total_por_fuente = {}
        if self.total_available_by_source is None:
            self.total_available_by_source = {}


@dataclass
class FinalSearchResult:
    """
    Resultado de una búsqueda final (con persistencia completa).

    Usado por Design cuando confirma la estrategia y los estudios a guardar.
    """
    execution_id: str
    strategy_id: str
    studies_persisted: List[str]  # IDs de estudios persistidos
    total_found: int
    new_studies_count: int
    duplicates_count: int
    executed_at: 'datetime.datetime'
    status: str


@dataclass
class EnrichmentStatusResult:
    """Resultado simplificado de enriquecimiento de metadatos."""
    enriched_count: int
    failed_count: int
    study_ids: List[str]  # IDs de estudios enriquecidos


@dataclass
class DownloadStatusResult:
    """Resultado simplificado de estado de descargas."""
    total_count: int
    downloaded_count: int
    available_count: int
    failed_count: int
    study_statuses: List[Dict[str, Any]]


# ==============================================================================
# FACADE PRINCIPAL
# ==============================================================================


class AcquisitionFacade:
    """
    Fachada principal del módulo de Acquisition.

    Provee una API simple y clara para que otros módulos (Design, Selection,
    Extraction) puedan utilizar las capacidades de Acquisition sin conocer los
    detalles internos de orquestación.

    Esta fachada:
    - Oculta la complejidad del AcquisitionOrchestrator
    - Provee métodos con nombres claros y enfocados al caso de uso
    - Maneja toda la trazabilidad internamente
    - Expone resultados simplificados (DTOs)
    """

    def __init__(self):
        """Inicializar la fachada usando el Container de inyección de dependencias."""
        # Importaciones locales para evitar ciclos
        from .container import Container

        self._orchestrator = Container.get_orchestrator()
        self._enrichment_service = Container.get_enrichment_service()
        self._fulltext_service = Container.get_fulltext_service_production()

        logger.info("AcquisitionFacade initialized")

    # ==========================================================================
    # MÉTODOS PARA DESIGN (Preview y Final)
    # ==========================================================================

    def preview_search(
        self,
        strategy_dict: Dict[str, Any],
        user: Optional[User] = None,
        max_results_per_source: int = DEFAULT_MAX_RESULTS_PER_SOURCE,
        selected_sources: Optional[List[str]] = None,
    ) -> PreviewSearchResult:
        """
        Ejecutar búsqueda en modo preview (SIN persistir nada en BD).

        Este método es usado por Design para:
        - Probar una cadena de búsqueda antes de confirmarla
        - Ver qué estudios retornaría sin contaminar la base de datos
        - Permitir al usuario seleccionar estudios relevantes
        - Filtrar por motores de búsqueda específicos

        Args:
            strategy_dict: Estrategia normalizada para ejecutar
            user: Usuario que solicita el preview (opcional)
            max_results_per_source: Límite de resultados por fuente académica
            selected_sources: Lista de fuentes a consultar (opcional).
                             Acepta nombres UI ("IEEE") o canónicos ("IEEE Xplore").
                             Si es None o vacío, consulta TODAS las fuentes disponibles.

        Returns:
            PreviewSearchResult con studies como dicts (sin IDs de BD)

        Raises:
            ValueError: Si la estrategia es inválida
            Exception: Si falla algún servicio crítico
            
        Examples:
            # Buscar solo en Scopus
            >>> facade.preview_search(strategy, selected_sources=["Scopus"])
            
            # Buscar solo en IEEE (acepta nombre UI)
            >>> facade.preview_search(strategy, selected_sources=["IEEE"])
            
            # Buscar en ambos (comportamiento por defecto)
            >>> facade.preview_search(strategy)
        """
        # BOUNDARY: Normalizar nombres UI → nombres internos canónicos
        normalized_sources = normalize_source_names(selected_sources)
        logger.info(f"[FACADE] Preview search starting with sources: {normalized_sources}")

        try:
            # Delegar al orchestrator con las fuentes filtradas
            preview_result = self._orchestrator.preview_search_from_strategy(
                strategy_dict=strategy_dict,
                user=user,
                max_results_per_source=max_results_per_source,
                selected_sources=normalized_sources,
            )

            # Convertir a DTO simplificado para Design
            return PreviewSearchResult(
                queries_by_source=preview_result["queries_by_source"],
                total_found=preview_result["total_found"],
                studies=preview_result["studies"],
                strategy_dict=strategy_dict,
                selected_sources=normalized_sources,  # Guardar para trazabilidad
                total_por_fuente=preview_result.get("total_por_fuente", {}),  # ✅ Cantidad limitada
                total_available_by_source=preview_result.get("total_available_by_source", {}),  # ✅ Total real
            )

        except Exception as e:
            logger.error(f"[FACADE] Preview search failed: {e}", exc_info=True)
            raise

    def get_translated_queries(
        self,
        strategy_dict: Dict[str, Any],
    ) -> Dict[str, str]:
        """
        Obtener las queries traducidas para cada fuente académica, sin ejecutar la búsqueda.
        
        Usado por Design para mostrar al usuario cómo se ve su estrategia en Scopus/IEEE.
        
        Args:
            strategy_dict: Estrategia visual/normalizada
            
        Returns:
            Dict[str, str]: Diccionario {Fuente: QueryString}
        """
        logger.info("[FACADE] Getting translated queries only")
        try:
            return self._orchestrator.translate_strategy_only(strategy_dict)
        except Exception as e:
            logger.error(f"[FACADE] Translation failed: {e}", exc_info=True)
            raise

    def finalize_search(
        self,
        design_strategy_id: int,
        preview_result: PreviewSearchResult,
        user: Optional[User] = None,
    ) -> FinalSearchResult:
        """
        Ejecutar búsqueda final y persistir todo (estrategia + estudios + trazabilidad).

        Este método es usado por Design cuando:
        - Confirma que una estrategia de búsqueda es la definitiva
        - Selecciona estudios específicos del preview para guardar
        - Quiere persistir con trazabilidad completa

        Flujo completo que ejecuta:
        1. Actualiza la estrategia en Design con la definición completa
        2. Persiste los estudios seleccionados en StudyModel
        3. Registra la ejecución en SearchExecutionModel
        4. Crea los vínculos en ExecutionStudy (trazabilidad M2M)
        5. Actualiza estadísticas en la estrategia de Design

        IMPORTANTE: Este método usa los datos del preview (queries_by_source, 
        selected_sources) para mantener trazabilidad consistente. NO re-traduce
        la estrategia, evitando inconsistencias entre preview y persist.

        Args:
            design_strategy_id: ID de la estrategia en design.SearchStrategy
            preview_result: Resultado del preview con estudios, estrategia y fuentes usadas
            user: Usuario que confirma la persistencia

        Returns:
            FinalSearchResult con IDs de estudios persistidos y trazabilidad completa

        Raises:
            ValueError: Si parámetros inválidos
            Exception: Si falla persistencia
        """
        logger.info(
            f"[FACADE] Finalize search for strategy {design_strategy_id} "
            f"with {len(preview_result.studies)} studies, "
            f"sources: {preview_result.selected_sources}"
        )

        try:
            # Delegar al orchestrator usando datos del preview (no re-traducir)
            execution_result = self._orchestrator.execute_and_persist_final(
                strategy_dict=preview_result.strategy_dict,
                design_strategy_id=design_strategy_id,
                selected_studies=preview_result.studies,
                user=user,
                queries_by_source=preview_result.queries_by_source,  # Del preview
                selected_sources=preview_result.selected_sources,     # Del preview
            )

            # Convertir a DTO simplificado para Design
            return FinalSearchResult(
                execution_id=execution_result.execution_id,
                strategy_id=execution_result.strategy_id,
                studies_persisted=[str(study.id) for study in execution_result.studies],
                total_found=execution_result.total_found,
                new_studies_count=execution_result.new_studies_count,
                duplicates_count=execution_result.duplicates_count,
                executed_at=execution_result.executed_at,
                status=execution_result.status,
            )

        except Exception as e:
            logger.error(f"[FACADE] Finalize search failed: {e}", exc_info=True)
            raise

    def get_enrichment_service(self):
        """
        Obtener servicio de enriquecimiento (para Selection/Extraction).

        Returns:
            EnrichmentService para consolidar metadatos de estudios
        """
        return self._enrichment_service

    def get_fulltext_service(self):
        """
        Obtener servicio de descarga de PDFs (para Extraction).

        Returns:
            FullTextService para descargar textos completos
        """
        return self._fulltext_service

    # ==========================================================================
    # MÉTODOS PARA SELECTION Y EXTRACTION
    # ==========================================================================

    def enrich_studies(
        self,
        study_ids: List[str],
    ) -> EnrichmentStatusResult:
        """
        Enriquecer metadatos de estudios ya descubiertos.

        Usado por módulo Selection para mejorar calidad de metadatos
        antes de pasar a Screening.

        Args:
            study_ids: Lista de UUIDs de estudios a enriquecer

        Returns:
            EnrichmentStatusResult con conteos e IDs procesados
        """
        logger.info(f"[FACADE] Enriching metadata for {len(study_ids)} studies")

        try:
            # Usar el orchestrator que ya delega al ConsolidationService
            enrichment_result = self._orchestrator.enrich_studies_metadata(
                study_ids=study_ids,
                consolidation_service=self._enrichment_service,
            )

            # Convertir a DTO simplificado
            return EnrichmentStatusResult(
                enriched_count=enrichment_result.enriched_count,
                failed_count=enrichment_result.failed_count,
                study_ids=[str(study.id) for study in enrichment_result.studies],
            )

        except Exception as e:
            logger.error(f"[FACADE] Studies enrichment failed: {e}", exc_info=True)
            raise

    def download_fulltexts(
        self,
        study_ids: List[str],
    ) -> DownloadStatusResult:
        """
        Descargar PDFs para estudios (usado por Extraction).

        Args:
            study_ids: Lista de UUIDs de estudios para descargar

        Returns:
            DownloadStatusResult con estado de descargas por estudio
        """
        logger.info(f"[FACADE] Downloading fulltexts for {len(study_ids)} studies")

        try:
            # Usar el orchestrator que ya delega al FullTextService
            download_stats = self._orchestrator.enqueue_downloads(
                study_ids=study_ids,
                fulltext_service=self._fulltext_service,
            )

            # Obtener estado actual de cada estudio
            study_statuses = self._orchestrator.get_download_status(study_ids)

            # Convertir a DTO simplificado
            return DownloadStatusResult(
                total_count=download_stats.get("enqueued_count", 0),
                downloaded_count=download_stats.get("downloaded_count", 0),
                available_count=download_stats.get("already_downloaded_count", 0),
                failed_count=download_stats.get("not_available_count", 0),
                study_statuses=study_statuses,
            )

        except Exception as e:
            logger.error(f"[FACADE] Fulltext download failed: {e}", exc_info=True)
            raise

    # ==========================================================================
    # MÉTODOS DE CONSULTA (para todos los módulos)
    # ==========================================================================

    def get_study_status(self, study_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Obtener estado actual de estudios (descarga, metadatos, etc.).

        Usado por cualquier módulo para consultar estado de estudios.

        Args:
            study_ids: Lista de UUIDs de estudios

        Returns:
            Lista de dicts con estado de cada estudio
        """
        logger.info(f"[FACADE] Getting status for {len(study_ids)} studies")

        try:
            return self._orchestrator.get_download_status(study_ids)
        except Exception as e:
            logger.error(f"[FACADE] Get study status failed: {e}", exc_info=True)
            raise

    def is_healthy(self) -> bool:
        """
        Verificar salud del módulo de Acquisition.

        Returns:
            True si todos los servicios críticos están disponibles
        """
        try:
            # Verificar que el orchestrator esté inicializado
            healthy = self._orchestrator is not None

            # Aquí se podrían agregar más verificaciones:
            # - Conectividad con repositorios
            # - Disponibilidad de servicios externos
            # - Estado de colas de tareas

            logger.info(f"[FACADE] Health check: {'✓' if healthy else '✗'}")
            return healthy

        except Exception as e:
            logger.error(f"[FACADE] Health check failed: {e}", exc_info=True)
            return False

    def get_studies_by_project(
        self,
        project_id: int,
        include_metadata: bool = True,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtener todos los estudios asociados a un proyecto.

        Usado por módulo Project para listar estudios de un proyecto SLR.
        Los estudios se obtienen a través de la cadena:
        Project → DesignPhase → ResearchQuestion → SearchStrategy → SearchExecution → Study

        Args:
            project_id: ID del proyecto (design.DesignPhase.project_id)
            include_metadata: Si True, incluye metadatos completos (authors, abstract, etc.)
            status_filter: Opcional, filtrar por estado (discovered, enriched, downloaded, failed)

        Returns:
            Lista de dicts con datos de cada estudio:
            - id: UUID del estudio
            - title: Título
            - source: Fuente académica
            - status: Estado del workflow
            - doi: DOI (si existe)
            - year: Año de publicación
            - download_status: Estado de disponibilidad del PDF
            - (si include_metadata=True): authors, abstract, keywords, journal
        """
        logger.info(f"[FACADE] Getting studies for project {project_id}")

        try:
            # Importación local para evitar ciclos
            from apps.acquisition.models import StudyModel, SearchExecutionModel
            from apps.design.search_strategy.models.search_strategy import SearchStrategy

            # Obtener todas las estrategias del proyecto
            strategies = SearchStrategy.objects.by_project(project_id)
            strategy_ids = list(strategies.values_list('id', flat=True))

            if not strategy_ids:
                logger.info(f"[FACADE] No strategies found for project {project_id}")
                return []

            # Obtener todas las ejecuciones de esas estrategias
            executions = SearchExecutionModel.objects.filter(
                strategy_id__in=strategy_ids
            )
            execution_ids = list(executions.values_list('id', flat=True))

            if not execution_ids:
                logger.info(f"[FACADE] No executions found for project {project_id}")
                return []

            # Obtener todos los estudios vinculados a esas ejecuciones
            # Usamos distinct() para evitar duplicados por M2M
            # Ordenamos por discovered_at para resultados consistentes
            studies_qs = StudyModel.objects.filter(
                executions__id__in=execution_ids
            ).distinct().order_by('-discovered_at')

            # Aplicar filtro de estado si se especifica
            if status_filter:
                studies_qs = studies_qs.filter(status=status_filter)

            # Construir respuesta
            result = []
            for study in studies_qs:
                study_dict = {
                    "id": str(study.uuid),
                    "title": study.title,
                    "link": study.link,
                    "source": study.source,
                    "status": study.status,
                    "doi": study.doi,
                    "year": study.year,
                    "download_status": study.download_status,
                    "pdf_path": study.pdf_path,
                    "consolidation_status": study.consolidation_status,
                    "discovered_at": study.discovered_at.isoformat() if study.discovered_at else None,
                }

                if include_metadata:
                    study_dict.update({
                        "authors": study.authors or [],
                        "abstract": study.abstract,
                        "keywords": study.keywords or [],
                        "journal": study.journal,
                        "field_origins": study.field_origins or {},
                    })

                result.append(study_dict)

            logger.info(f"[FACADE] Found {len(result)} studies for project {project_id}")
            return result

        except Exception as e:
            logger.error(f"[FACADE] Get studies by project failed: {e}", exc_info=True)
            raise

    # ==========================================================================
    # MÉTODOS PARA GESTIÓN MANUAL (Fallback cuando los robots fallan)
    # ==========================================================================

    def register_manual_study(
        self,
        study_data: Dict[str, Any],
        strategy_id: Optional[str] = None,
        user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Registrar un estudio manualmente (cuando no aparece en búsquedas).

        Permite agregar estudios que:
        - No fueron encontrados por los conectores académicos
        - Provienen de fuentes no automatizadas (ej. conferencias locales)
        - El usuario encontró en físico o referencias cruzadas

        Args:
            study_data: Dict con keys: title, link, doi, authors, year, abstract, keywords, etc.
            strategy_id: ID de la estrategia de búsqueda a la que asociar (opcional)
            user: Usuario que realiza la acción (opcional)

        Returns:
            Dict con los datos del estudio creado (id, title, status)

        Raises:
            ValueError: Si faltan campos requeridos (title, link)
            Exception: Si falla la persistencia
        """
        logger.info(f"[FACADE] Registering manual study: {study_data.get('title')}")

        try:
            study = self._orchestrator.add_manual_study(study_data, user, strategy_id)

            # Retornar DTO simple (dict)
            return study.to_dict()

        except Exception as e:
            logger.error(f"[FACADE] Manual study registration failed: {e}", exc_info=True)
            raise

    def update_study_metadata(
        self,
        study_id: str,
        updates: Dict[str, Any],
        user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Actualizar metadatos de un estudio manualmente.

        Permite corregir:
        - Errores en metadatos automáticamente recolectados
        - Campos faltantes (año, DOI, autores)
        - Información incorrecta o desactualizada

        Args:
            study_id: UUID del estudio
            updates: Dict con los campos a modificar (doi, year, authors, abstract, etc.)
            user: Usuario que realiza la corrección (opcional)

        Returns:
            Dict con los datos del estudio actualizado

        Raises:
            ValueError: Si no se encuentra el estudio
            Exception: Si falla la actualización
        """
        logger.info(f"[FACADE] Updating metadata for study {study_id}")

        try:
            study = self._orchestrator.update_study_metadata_manually(study_id, updates, user)
            return study.to_dict()

        except Exception as e:
            logger.error(f"[FACADE] Manual metadata update failed: {e}", exc_info=True)
            raise

    def upload_study_pdf(
        self,
        study_id: str,
        file_obj: Any,
        filename: str,
        user: Optional[User] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Subir un archivo PDF manualmente para un estudio.

        Permite subir PDFs cuando:
        - El texto completo no está disponible online (Open Access)
        - El usuario tiene acceso institucional no automatizable
        - El paper está en físico y fue escaneado
        - Se necesita reemplazar un PDF corrupto o incorrecto (force=True)

        Args:
            study_id: UUID del estudio
            file_obj: Objeto archivo (Django UploadedFile o similar)
            filename: Nombre del archivo
            user: Usuario que sube el archivo (opcional)
            force: Si True, permite reemplazar un PDF existente

        Returns:
            Dict con study_id, pdf_path, download_status

        Raises:
            ValueError: Si el estudio no existe o el archivo no es PDF válido
            Exception: Si falla el almacenamiento
        """
        logger.info(f"[FACADE] Uploading PDF for study {study_id} (force={force})")

        try:
            # Delegar al orquestador (que a su vez delega al ManualUploadAppService)
            study = self._orchestrator.upload_study_pdf(study_id, file_obj, filename, user, force)

            return {
                "study_id": str(study.id),
                "pdf_path": study.pdf_path,
                "download_status": study.download_status
            }

        except Exception as e:
            logger.error(f"[FACADE] Manual PDF upload failed: {e}", exc_info=True)
            raise

    def __str__(self):
        """Representación string del fachada."""
        return "AcquisitionFacade(Design↔Acquisition Bridge)"


# ==============================================================================
# FUNCIÓN DE CONVENIENCIA - Instancia global
# ==============================================================================


# Instancia global de la fachada para fácil acceso desde otros módulos
_facade_instance = None


def get_acquisition_facade() -> AcquisitionFacade:
    """
    Obtener instancia global de la fachada de Acquisition.

    Esta función permite que otros módulos obtengan la fachada
    sin necesidad de conocer los detalles de inicialización.

    Returns:
        AcquisitionFacade: Instancia inicializada de la fachada
    """
    global _facade_instance

    if _facade_instance is None:
        _facade_instance = AcquisitionFacade()
        logger.info("Global AcquisitionFacade instance created")

    return _facade_instance


# ==============================================================================
# EJEMPLOS DE USO (documentación para otros desarrolladores)
# ==============================================================================

"""
EJEMPLOS DE USO desde otros módulos:

# Desde Design:
from apps.acquisition.facade import get_acquisition_facade

facade = get_acquisition_facade()

# 1. Preview de búsqueda
preview = facade.preview_search(strategy_dict, user=current_user)
print(f"Preview encontró {preview.total_found} estudios")

# 2. Usuario selecciona estudios (filtrar el DTO)
preview.studies = preview.studies[:10]  # Usuario selecciona 10

# 3. Persistir resultados seleccionados
if user_confirms:
    final_result = facade.finalize_search(
        design_strategy_id=strategy.id,
        preview_result=preview,  # DTO completo con estudios seleccionados
        user=current_user,
    )
    print(f"Persistidos {final_result.new_studies_count} estudios nuevos")

# Desde Selection:
facade = get_acquisition_facade()
enrichment_result = facade.enrich_studies(study_ids)
print(f"Enriquecidos {enrichment_result.enriched_count} estudios")

# Desde Extraction:
facade = get_acquisition_facade()
download_result = facade.download_fulltexts(study_ids)
print(f"Descargados {download_result.downloaded_count} PDFs")

# Desde Project (obtener todos los estudios de un proyecto):
facade = get_acquisition_facade()
project_studies = facade.get_studies_by_project(project_id=1)
print(f"El proyecto tiene {len(project_studies)} estudios")

# Filtrar solo estudios descargados:
downloaded_studies = facade.get_studies_by_project(
    project_id=1, 
    status_filter="downloaded"
)
print(f"Estudios con PDF disponible: {len(downloaded_studies)}")

# Gestión Manual (cuando los robots fallan):
facade = get_acquisition_facade()

# Registrar estudio manual
study_dict = facade.register_manual_study({
    "title": "Manual Study Title",
    "link": "https://example.com/paper",
    "doi": "10.1234/example",
    "year": 2023,
    "authors": ["John Doe", "Jane Smith"]
}, user=current_user)

# Actualizar metadatos
updated_study = facade.update_study_metadata(
    study_id="uuid-here",
    updates={"year": 2024, "abstract": "Corrected abstract"},
    user=current_user
)

# Subir PDF manual
pdf_result = facade.upload_study_pdf(
    study_id="uuid-here",
    file_obj=uploaded_file,
    filename="paper.pdf",
    user=current_user
)
"""
