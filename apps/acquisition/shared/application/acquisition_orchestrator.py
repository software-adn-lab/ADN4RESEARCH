"""
AcquisitionOrchestrator - Orquestador principal del módulo de Adquisición.

Este servicio de aplicación coordina todo el flujo del módulo:
1. Traducción de estrategias (Translation)
2. Descubrimiento de estudios (Discovery)
3. Enriquecimiento de metadatos (Metadata)
4. Descarga de textos completos (Downloads)
5. Persistencia y trazabilidad (Repositories + Models)

Arquitectura:
- Capa de Aplicación (Application Layer) - Coordinación de casos de uso
- NO contiene lógica de dominio, solo orquesta servicios
- Maneja transacciones y persistencia
- Conecta con otros módulos (Design)
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from django.db import transaction
from django.contrib.auth import get_user_model

# Domain
from apps.acquisition.translation.domain.models import NormalizedStrategy
from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.shared.domain.repositories.i_study_repository import IStudyRepository

# Application Services
from apps.acquisition.translation.application.translation_service import TranslationService
from apps.acquisition.discovery.application.discovery_service import DiscoveryService

# Infrastructure (ORM Models)
from apps.acquisition.models import (
    SearchStrategyModel,
    SearchExecutionModel,
    ExecutionStudy,
    StudyModel,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ==============================================================================
# DATA TRANSFER OBJECTS (DTOs)
# ==============================================================================


@dataclass
class SearchExecutionResult:
    """
    Resultado de ejecutar una búsqueda completa.

    Este DTO encapsula todo lo que sucedió en una ejecución:
    - La estrategia usada
    - La ejecución registrada en BD
    - Los estudios encontrados
    - Estadísticas y trazabilidad
    """

    execution_id: str
    strategy_id: str
    studies: List[Study]
    total_found: int
    new_studies_count: int
    duplicates_count: int
    queries_by_source: Dict[str, str]
    executed_at: datetime
    status: str  # "SUCCESS", "PARTIAL", "FAILED"
    errors: Dict[str, str] = None  # Errores por proveedor


@dataclass
class EnrichmentResult:
    """Resultado de enriquecer metadatos de estudios."""

    enriched_count: int
    failed_count: int
    studies: List[Study]


# ==============================================================================
# ORCHESTRATOR
# ==============================================================================


class AcquisitionOrchestrator:
    """
    Orquestador principal del módulo de Adquisición.

    Coordina el flujo completo desde la estrategia de búsqueda hasta
    los estudios persistidos con metadatos y PDFs.

    Responsabilidades:
    1. Ejecutar búsqueda desde estrategia normalizada:
       - Traducir estrategia a queries específicas por proveedor
       - Ejecutar discovery en paralelo en múltiples proveedores
       - Deduplicar y persistir estudios
       - Registrar ejecución con trazabilidad completa
    2. Enriquecer metadatos de estudios ya descubiertos
    3. Encolar descargas de PDFs
    4. Consultar estado de descargas

    Integración con otros módulos:
    - Design: Vincula estrategias con ResearchQuestion
    - Selection: Provee estudios para screening
    - Extraction: Provee estudios con PDFs para extracción
    """

    def __init__(
        self,
        translation_service: TranslationService,
        discovery_service: DiscoveryService,
        study_repository: IStudyRepository,
    ):
        """
        Inicializar el orquestador con servicios inyectados.

        Args:
            translation_service: Servicio de traducción de estrategias
            discovery_service: Servicio de descubrimiento de estudios
            study_repository: Repositorio de persistencia de estudios
        """
        self.translation_service = translation_service
        self.discovery_service = discovery_service
        self.study_repository = study_repository

        logger.info("AcquisitionOrchestrator initialized")

    # ==========================================================================
    # USE CASE 1: Ejecutar búsqueda completa desde estrategia
    # ==========================================================================

    @transaction.atomic
    def execute_search_from_strategy(
        self,
        strategy_dict: Dict[str, Any],
        research_question_id: Optional[int] = None,
        user: Optional[User] = None,
        strategy_name: Optional[str] = None,
        strategy_description: Optional[str] = None,
    ) -> SearchExecutionResult:
        """
        Ejecutar búsqueda completa desde una estrategia normalizada.

        Flujo completo:
        1. Persistir estrategia en BD (SearchStrategyModel)
        2. Convertir dict → NormalizedStrategy (dominio)
        3. Traducir estrategia a queries por proveedor (TranslationService)
        4. Ejecutar discovery en paralelo (DiscoveryService)
        5. Persistir estudios encontrados (StudyRepository)
        6. Registrar ejecución con trazabilidad (SearchExecutionModel + ExecutionStudy)

        Args:
            strategy_dict: Diccionario con la estrategia normalizada
                          {"strategy_id": str, "main_terms": [...], "exclusions": [...], "filters": {...}}
            research_question_id: ID de la pregunta de investigación (integración con Design)
            user: Usuario que ejecuta la búsqueda
            strategy_name: Nombre descriptivo de la estrategia
            strategy_description: Descripción de la estrategia

        Returns:
            SearchExecutionResult con toda la información de la ejecución

        Raises:
            ValueError: Si la estrategia es inválida
            Exception: Si falla algún servicio crítico
        """
        logger.info(f"Starting search execution for strategy: {strategy_dict.get('strategy_id')}")

        # 1. Persistir estrategia
        strategy_model = self._create_strategy_model(
            strategy_dict=strategy_dict,
            research_question_id=research_question_id,
            user=user,
            name=strategy_name,
            description=strategy_description,
        )
        logger.info(f"Strategy persisted: {strategy_model.id}")

        # 2. Convertir a dominio
        normalized_strategy = NormalizedStrategy.from_dict(strategy_dict)

        # 3. Traducir estrategia a queries por proveedor
        translation_results = self._translate_strategy(normalized_strategy)
        queries_by_source = translation_results["queries_by_source"]
        translation_statuses = translation_results["translation_statuses"]

        logger.info(f"Strategy translated to {len(queries_by_source)} providers")

        # 4. Ejecutar discovery
        discovery_result = self.discovery_service.execute(
            strategy_id=normalized_strategy.strategy_id,
            translation_statuses=translation_statuses,
            supported_sources=list(queries_by_source.keys()),
            max_results_per_source=25,  # TODO: Hacer configurable
        )

        logger.info(
            f"Discovery completed: {discovery_result.total_unique_studies} unique studies "
            f"(from {discovery_result.total_raw_studies} raw)"
        )

        # 5. Los estudios ya fueron persistidos por DiscoveryService
        # (DiscoveryService tiene repositorio inyectado y persiste automáticamente)
        persisted_studies = discovery_result.studies

        # 6. Registrar ejecución con trazabilidad
        execution_model = self._create_execution_model(
            strategy_model=strategy_model,
            queries_by_source=queries_by_source,
            discovery_result=discovery_result,
            user=user,
        )

        # 7. Vincular estudios con ejecución (tabla M2M ExecutionStudy)
        if persisted_studies:
            self._link_studies_to_execution(
                execution_model=execution_model,
                studies=persisted_studies,
                results_by_source=discovery_result.results_by_source,
            )

        logger.info(f"Execution registered: {execution_model.id}")

        # 8. Construir resultado
        return SearchExecutionResult(
            execution_id=str(execution_model.id),
            strategy_id=str(strategy_model.id),
            studies=persisted_studies,
            total_found=discovery_result.total_unique_studies,
            new_studies_count=execution_model.new_studies_count,
            duplicates_count=discovery_result.total_raw_studies - discovery_result.total_unique_studies,
            queries_by_source=queries_by_source,
            executed_at=execution_model.executed_at,
            status=execution_model.status,
            errors=discovery_result.errors if hasattr(discovery_result, 'errors') else None,
        )

    # ==========================================================================
    # USE CASE 2: Enriquecer metadatos de estudios
    # ==========================================================================

    def enrich_studies_metadata(
        self,
        study_ids: List[str],
        consolidation_service: Optional[Any] = None,  # ConsolidationService
    ) -> EnrichmentResult:
        """
        Enriquecer metadatos de estudios ya descubiertos.

        Delega la consolidación a ConsolidationService.

        Args:
            study_ids: Lista de IDs de estudios a enriquecer
            consolidation_service: Servicio de consolidación (inyectado)

        Returns:
            EnrichmentResult con estadísticas del enriquecimiento

        Raises:
            ValueError: Si consolidation_service no está inyectado
            ValueError: Si no se encuentran estudios
        """
        if consolidation_service is None:
            raise ValueError(
                "consolidation_service debe ser inyectado. "
                "Usar Container.get_consolidation_service()"
            )

        logger.info(f"Enriching metadata for {len(study_ids)} studies")

        # Delegar a ConsolidationService (que hace todo el flujo con persistencia)
        consolidation_result = consolidation_service.enrich_studies(study_ids)

        # Convertir ConsolidationResult a EnrichmentResult
        return EnrichmentResult(
            enriched_count=consolidation_result.summary["successful"],
            failed_count=consolidation_result.summary["failed"],
            studies=consolidation_result.studies,
        )

    # ==========================================================================
    # USE CASE 3: Gestionar descargas de PDFs
    # ==========================================================================

    def enqueue_downloads(
        self,
        study_ids: List[str],
        fulltext_service: Optional[Any] = None,  # FullTextService
    ) -> Dict[str, Any]:
        """
        Descargar PDFs automáticamente para estudios.

        Delega la descarga a FullTextService.

        Args:
            study_ids: Lista de IDs de estudios para descargar PDFs
            fulltext_service: Servicio de descarga (inyectado)

        Returns:
            Dict con estadísticas de descarga

        Raises:
            ValueError: Si fulltext_service no está inyectado
        """
        if fulltext_service is None:
            raise ValueError(
                "fulltext_service debe ser inyectado. "
                "Usar Container.get_fulltext_service_production()"
            )

        logger.info(f"Downloading fulltexts for {len(study_ids)} studies")

        # Delegar a FullTextService (que hace todo el flujo con persistencia)
        download_stats = fulltext_service.download_batch(study_ids)

        # Adaptar nombres de campos al contrato esperado
        return {
            "enqueued_count": download_stats["total"],
            "already_downloaded_count": download_stats["already_available"],
            "downloaded_count": download_stats["downloaded"],
            "not_available_count": download_stats["not_available"],
            "failed_count": download_stats["errors"],
        }

    def get_download_status(self, study_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Obtener estado de descargas de PDFs.

        Args:
            study_ids: Lista de IDs de estudios

        Returns:
            Lista de dicts con info de descarga por estudio
        """
        results = []
        for study_id in study_ids:
            study = self.study_repository.find_by_id(study_id)
            if study:
                results.append(
                    {
                        "study_id": study.id,
                        "title": study.title,
                        "download_status": study.download_status,
                        "pdf_path": study.pdf_path,
                        "pdf_source": study.pdf_source,
                    }
                )
        return results

    # ==========================================================================
    # HELPER METHODS (Privados)
    # ==========================================================================

    def _create_strategy_model(
        self,
        strategy_dict: Dict[str, Any],
        research_question_id: Optional[int],
        user: Optional[User],
        name: Optional[str],
        description: Optional[str],
    ) -> SearchStrategyModel:
        """Crear y persistir SearchStrategyModel."""
        research_question = None
        if research_question_id:
            from apps.design.research_question.models.research_question import ResearchQuestion

            try:
                research_question = ResearchQuestion.objects.get(id=research_question_id)
            except ResearchQuestion.DoesNotExist:
                logger.warning(f"ResearchQuestion {research_question_id} not found")

        strategy_model = SearchStrategyModel.objects.create(
            research_question=research_question,
            definition=strategy_dict,
            name=name or f"Strategy {strategy_dict.get('strategy_id', 'unnamed')}",
            description=description,
            created_by=user,
        )

        return strategy_model

    def _translate_strategy(self, normalized_strategy: NormalizedStrategy) -> Dict[str, Any]:
        """
        Traducir estrategia a queries por proveedor.

        Returns:
            {
                "queries_by_source": {"Scopus": "...", "IEEE Xplore": "..."},
                "translation_statuses": {...}
            }
        """
        # Traducir a todos los proveedores soportados
        from apps.acquisition.shared.domain.constants import SUPPORTED_SOURCES

        queries_by_source = {}
        translation_statuses = {}

        for source in SUPPORTED_SOURCES:
            try:
                translation_result = self.translation_service.translate(
                    strategy=normalized_strategy, target=source
                )
                queries_by_source[source] = translation_result["output_query"]
                translation_statuses[source] = translation_result
            except Exception as e:
                logger.error(f"Failed to translate strategy for {source}: {e}")
                translation_statuses[source] = {
                    "status": "failed",
                    "error": str(e),
                }

        return {
            "queries_by_source": queries_by_source,
            "translation_statuses": translation_statuses,
        }

    def _create_execution_model(
        self,
        strategy_model: SearchStrategyModel,
        queries_by_source: Dict[str, str],
        discovery_result: Any,  # DiscoveryResult
        user: Optional[User],
    ) -> SearchExecutionModel:
        """Crear y persistir SearchExecutionModel."""
        # Determinar status de ejecución
        status = "SUCCESS"
        error_details = {}

        if hasattr(discovery_result, "not_executed_sources") and discovery_result.not_executed_sources:
            status = "PARTIAL"
            error_details["not_executed_sources"] = discovery_result.not_executed_sources

        if hasattr(discovery_result, "errors") and discovery_result.errors:
            if not discovery_result.studies:
                status = "FAILED"
            else:
                status = "PARTIAL"
            error_details["errors"] = discovery_result.errors

        execution_model = SearchExecutionModel.objects.create(
            strategy=strategy_model,
            executed_by=user,
            translated_queries={"queries_by_source": queries_by_source},
            results_count=discovery_result.total_unique_studies,
            new_studies_count=discovery_result.total_unique_studies,  # Será ajustado en _link_studies_to_execution
            status=status,
            error_details=error_details,
        )

        return execution_model

    def _link_studies_to_execution(
        self,
        execution_model: SearchExecutionModel,
        studies: List[Study],
        results_by_source: Dict[str, List[Study]],
    ) -> None:
        """
        Vincular estudios con ejecución usando tabla M2M ExecutionStudy.

        MEJORES PRÁCTICAS:
        - Usa bulk_create para crear todos los vínculos de una vez (performance)
        - Detecta correctamente si el estudio es nuevo vs duplicado
        - Registra de qué proveedores vino cada estudio
        - Actualiza contador de nuevos en la ejecución
        """
        # Construir mapa de study_id → proveedores
        study_to_providers = {}
        for source, source_studies in results_by_source.items():
            for study in source_studies:
                if study.id not in study_to_providers:
                    study_to_providers[study.id] = []
                study_to_providers[study.id].append(source)

        # Crear vínculos ExecutionStudy
        execution_studies = []
        new_count = 0

        for idx, study in enumerate(studies):
            # DETECTAR SI ES NUEVO: El repositorio marca _was_new
            is_new = getattr(study, '_was_new', True)

            if is_new:
                new_count += 1

            providers = study_to_providers.get(study.id, [])

            execution_studies.append(
                ExecutionStudy(
                    execution=execution_model,
                    study_id=study.id,  # UUID
                    is_new=is_new,
                    providers=providers,
                    rank_position=idx + 1,
                )
            )

        # BULK CREATE para performance (1000 vínculos en ~50ms)
        ExecutionStudy.objects.bulk_create(execution_studies, ignore_conflicts=True)

        # Actualizar contador de nuevos en la ejecución
        execution_model.new_studies_count = new_count
        execution_model.save(update_fields=["new_studies_count"])

        logger.info(
            f"Linked {len(execution_studies)} studies to execution {execution_model.id} "
            f"({new_count} new, {len(studies) - new_count} duplicates)"
        )
