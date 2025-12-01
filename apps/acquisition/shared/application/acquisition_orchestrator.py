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
from apps.design.search_strategy.models.search_strategy import SearchStrategy

# Application Services
from apps.acquisition.translation.application.translation_service import TranslationService
from apps.acquisition.discovery.application.discovery_service import DiscoveryService

# Infrastructure (ORM Models)
from apps.acquisition.models import (
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
    los estudios persistidos con metadatos y PDFs.ha

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
        manual_upload_service=None,  # Inyección de dependencia
    ):
        """
        Inicializar el orquestador con servicios inyectados.

        Args:
            translation_service: Servicio de traducción de estrategias
            discovery_service: Servicio de descubrimiento de estudios
            study_repository: Repositorio de persistencia de estudios
            manual_upload_service: Servicio de carga manual de PDFs (opcional)
        """
        self.translation_service = translation_service
        self.discovery_service = discovery_service
        self.study_repository = study_repository
        self.manual_upload_service = manual_upload_service

        logger.info("AcquisitionOrchestrator initialized")

    # ==========================================================================
    # USE CASE 1: Preview de búsqueda (SIN persistir)
    # ==========================================================================

    def preview_search_from_strategy(
        self,
        strategy_dict: Dict[str, Any],
        user: Optional[User] = None,
        max_results_per_source: int = 25,
    ) -> Dict[str, Any]:
        """
        Piloto: traduce y ejecuta la estrategia pero NO persiste nada.
        Devuelve solo un arreglo de estudios (dicts) para Design.

        Args:
            strategy_dict: Diccionario con la estrategia normalizada
            user: Usuario que ejecuta la búsqueda (opcional para preview)
            max_results_per_source: Máximo de resultados por fuente

        Returns:
            Dict con:
            - queries_by_source: Dict[str, str] - Queries traducidas
            - total_found: int - Total de estudios únicos encontrados
            - studies: List[Dict] - Estudios como dicts (sin persistir)
        """
        logger.info(f"[PREVIEW] strategy: {strategy_dict.get('strategy_id')}")

        # Convertir a dominio
        normalized_strategy = NormalizedStrategy.from_dict(strategy_dict)

        # Traducir estrategia a queries por proveedor
        translation_results = self._translate_strategy(normalized_strategy)
        queries_by_source = translation_results["queries_by_source"]
        translation_statuses = translation_results["translation_statuses"]

        # Ejecutar discovery SIN persistir
        discovery_result = self.discovery_service.execute(
            strategy_id=normalized_strategy.strategy_id,
            translation_statuses=translation_statuses,
            supported_sources=list(queries_by_source.keys()),
            max_results_per_source=max_results_per_source,
            persist=False,  # MUY IMPORTANTE: no persistir
        )

        # Convertir estudios a dicts para Design (sin tocar BD)
        studies_payload = []
        for idx, study in enumerate(discovery_result.studies):
            studies_payload.append(
                {
                    "id": str(study.id),
                    "title": study.title,
                    "link": study.link,
                    "source": study.source,
                    "doi": study.doi,
                    "year": study.year,
                    "authors": study.authors or [],
                    "abstract": study.abstract,
                    "journal": study.journal,
                    "keywords": study.keywords or [],
                    "is_open_access": study.is_open_access,  # ✅ AGREGADO
                    "pdf_url": study.pdf_url,  # ✅ AGREGADO
                    "providers": [study.source],
                    "rank_position": idx + 1,
                }
            )

        return {
            "queries_by_source": queries_by_source,
            "total_found": discovery_result.total_unique_studies,
            "studies": studies_payload,
        }

    # ==========================================================================
    # USE CASE 2: Ejecutar y persistir búsqueda FINAL
    # ==========================================================================

    @transaction.atomic
    def execute_and_persist_final(
        self,
        strategy_dict: Dict[str, Any],
        design_strategy_id: int,
        selected_studies: List[Dict[str, Any]],
        user: Optional[User] = None,
    ) -> SearchExecutionResult:
        """
        Flujo FINAL: persiste estrategia + estudios + ejecución + trazabilidad.

        Args:
            strategy_dict: Diccionario con la estrategia normalizada
            design_strategy_id: ID de la estrategia en design.SearchStrategy
            selected_studies: Estudios seleccionados por Design para persistir
            user: Usuario que ejecuta la búsqueda

        Returns:
            SearchExecutionResult con toda la información de la ejecución
        """
        from apps.design.search_strategy.models.search_strategy import SearchStrategy

        # Obtener estrategia unificada de Design
        strategy = SearchStrategy.objects.get(id=design_strategy_id)

        # Actualizar definición en la estrategia unificada
        strategy.definition = strategy_dict
        strategy.start_execution(user)

        logger.info(f"[FINAL] Executing strategy {design_strategy_id} with {len(selected_studies)} studies")

        # Traducir estrategia para obtener queries (trazabilidad completa)
        normalized_strategy = NormalizedStrategy.from_dict(strategy_dict)
        translation_results = self._translate_strategy(normalized_strategy)
        queries_by_source = translation_results["queries_by_source"]

        # Convertir estudios seleccionados a entidades de dominio
        study_entities = []
        for raw in selected_studies:
            study_entities.append(
                Study.from_dict(
                    {
                        "id": raw.get("id"),
                        "title": raw["title"],
                        "link": raw["link"],
                        "source": raw["source"],
                        "doi": raw.get("doi"),
                        "authors": raw.get("authors", []),
                        "abstract": raw.get("abstract"),
                        "year": raw.get("year"),
                        "journal": raw.get("journal"),
                        "keywords": raw.get("keywords", []),
                        "is_open_access": raw.get("is_open_access"),  # ✅ AGREGADO
                        "pdf_url": raw.get("pdf_url"),  # ✅ AGREGADO
                        "pdf_path": raw.get("pdf_path"),
                        "pdf_source": raw.get("pdf_source"),
                        "download_status": raw.get("download_status"),
                        "field_origins": raw.get("field_origins", {}),
                    }
                )
            )

        # Persistir estudios seleccionados
        persisted_studies = self.study_repository.save_batch(study_entities)

        # Crear modelo de ejecución con trazabilidad completa
        execution_model = SearchExecutionModel.objects.create(
            strategy=strategy,
            executed_by=user,
            translated_queries={"queries_by_source": queries_by_source},  # ← TRAZABILIDAD COMPLETA
            results_count=len(persisted_studies),
            new_studies_count=0,  # Se ajusta abajo
            status="SUCCESS",
            error_details={},
        )

        # Crear vínculos ExecutionStudy
        execution_links = []
        new_count = 0
        for idx, (entity, raw) in enumerate(zip(persisted_studies, selected_studies)):
            is_new = getattr(entity, "_was_new", True)
            if is_new:
                new_count += 1

            execution_links.append(
                ExecutionStudy(
                    execution=execution_model,
                    study_id=entity.id,
                    is_new=is_new,
                    providers=raw.get("providers", [entity.source]),
                    rank_position=raw.get("rank_position", idx + 1),
                )
            )

        ExecutionStudy.objects.bulk_create(execution_links, ignore_conflicts=True)

        # Actualizar contador de nuevos estudios
        execution_model.new_studies_count = new_count
        execution_model.save(update_fields=["new_studies_count"])

        # Actualizar estadísticas en la estrategia
        strategy.complete_execution(len(persisted_studies), new_count)

        logger.info(f"[FINAL] Persisted {len(persisted_studies)} studies ({new_count} new) for execution {execution_model.id}")

        # Construir resultado
        return SearchExecutionResult(
            execution_id=str(execution_model.id),
            strategy_id=str(strategy.id),
            studies=persisted_studies,
            total_found=len(persisted_studies),
            new_studies_count=new_count,
            duplicates_count=len(persisted_studies) - new_count,
            queries_by_source=execution_model.translated_queries.get("queries_by_source", {}),
            executed_at=execution_model.executed_at,
            status=execution_model.status,
            errors=execution_model.error_details,
        )

    # ==========================================================================
    # USE CASE 3: Ejecutar búsqueda completa (LEGACY - mantiene compatibilidad)
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
        LEGADO: Ejecutar búsqueda completa desde estrategia (método original).

        Este método mantiene compatibilidad con código existente pero
        idealmente debería reemplazarse por execute_and_persist_final.
        """
        logger.info(f"[LEGACY] Full execution for strategy: {strategy_dict.get('strategy_id')}")

        # Crear o obtener estrategia unificada de Design
        strategy_model = self._get_or_create_unified_strategy(
            strategy_dict=strategy_dict,
            research_question_id=research_question_id,
            user=user,
            name=strategy_name,
            description=strategy_description,
        )
        logger.info(f"Unified strategy: {strategy_model.id}")

        # Convertir a dominio
        normalized_strategy = NormalizedStrategy.from_dict(strategy_dict)

        # Traducir estrategia a queries por proveedor
        translation_results = self._translate_strategy(normalized_strategy)
        queries_by_source = translation_results["queries_by_source"]
        translation_statuses = translation_results["translation_statuses"]

        logger.info(f"Strategy translated to {len(queries_by_source)} providers")

        # Ejecutar discovery CON persistir
        discovery_result = self.discovery_service.execute(
            strategy_id=normalized_strategy.strategy_id,
            translation_statuses=translation_statuses,
            supported_sources=list(queries_by_source.keys()),
            max_results_per_source=25,
            persist=True,
        )

        logger.info(
            f"Discovery completed: {discovery_result.total_unique_studies} unique studies "
            f"(from {discovery_result.total_raw_studies} raw)"
        )

        # Los estudios ya fueron persistidos por DiscoveryService
        persisted_studies = discovery_result.studies

        # Registrar ejecución con trazabilidad
        execution_model = self._create_execution_model(
            strategy_model=strategy_model,
            queries_by_source=queries_by_source,
            discovery_result=discovery_result,
            user=user,
        )

        # Vincular estudios con ejecución (tabla M2M ExecutionStudy)
        if persisted_studies:
            self._link_studies_to_execution(
                execution_model=execution_model,
                studies=persisted_studies,
                results_by_source=discovery_result.results_by_source,
            )

        logger.info(f"Execution registered: {execution_model.id}")

        # Construir resultado
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
        Obtener estado de descargas de PDFs y metadatos completos.

        Args:
            study_ids: Lista de IDs de estudios

        Returns:
            Lista de dicts con info completa por estudio
        """
        results = []
        for study_id in study_ids:
            study = self.study_repository.find_by_id(study_id)
            if study:
                # Usar to_dict() para obtener todos los campos
                study_dict = study.to_dict()
                # Mantener compatibilidad con código existente que espera 'study_id'
                study_dict['study_id'] = study.id
                results.append(study_dict)
        return results

    # ==========================================================================
    # HELPER METHODS (Privados)
    # ==========================================================================

    def _get_or_create_unified_strategy(
        self,
        strategy_dict: Dict[str, Any],
        research_question_id: Optional[int],
        user: Optional[User],
        name: Optional[str],
        description: Optional[str],
    ):
        """
        LEGADO: Este método mantiene compatibilidad pero ya no crea SearchStrategyModel.

        En el nuevo diseño:
        - Design crea SearchStrategy directamente
        - Acquisition solo vincula ejecuciones a SearchStrategy existentes
        """
        from apps.design.search_strategy.models.search_strategy import SearchStrategy as UnifiedSearchStrategy

        logger.warning(
            "[LEGACY] _get_or_create_unified_strategy called. "
            "Design should create SearchStrategy directly now."
        )

        # Buscar estrategia existente en Design
        if research_question_id:
            existing_strategy = UnifiedSearchStrategy.objects.filter(
                research_question_id=research_question_id,
                status=UnifiedSearchStrategy.Status.FINAL  # ← Buscar versiones finales
            ).first()

            if existing_strategy:
                logger.info(f"Found existing final strategy: {existing_strategy.id}")
                # Actualizar definición si es diferente
                if existing_strategy.definition != strategy_dict:
                    existing_strategy.definition = strategy_dict
                    existing_strategy.save(update_fields=['definition'])
                return existing_strategy

        # Crear nueva estrategia en Design (fallback para legacy)
        strategy_name = name or f"Search Strategy {strategy_dict.get('strategy_id', 'unnamed')[:8]}"
        strategy = UnifiedSearchStrategy.objects.create(
            research_question_id=research_question_id,
            name=strategy_name,
            definition=strategy_dict,
            created_by=user,
            status=UnifiedSearchStrategy.Status.READY,  # Lista para ejecución
        )

        logger.info(f"Created new SearchStrategy in Design: {strategy.id}")
        return strategy

    def _translate_strategy(self, normalized_strategy: NormalizedStrategy) -> Dict[str, Any]:
        """
        Traducir estrategia a queries por proveedor.

        Returns:
            {
                "queries_by_source": {"Scopus": "...", "IEEE Xplore": "..."},
                "translation_statuses": {...}
            }
        """
        # Traducir SOLO a proveedores de DISCOVERY (Scopus, IEEE)
        # NO traducir a Crossref ni Manual (esos son para enriquecimiento/manual)
        from apps.acquisition.shared.domain.constants import DISCOVERY_SOURCES

        queries_by_source = {}
        translation_statuses = {}

        for source in DISCOVERY_SOURCES:
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
        strategy_model,  # Ahora es design.SearchStrategy
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

    # ==========================================================================
    # USE CASE 4: Gestión Manual (Cuando los robots fallan o se necesita intervención humana)
    # ==========================================================================

    def add_manual_study(self, study_data: Dict[str, Any], user: Optional[User] = None) -> Study:
        """
        Registra un estudio manualmente (ej. el usuario lo tiene en físico).

        Este método permite:
        1. Agregar estudios que no fueron encontrados por los robots
        2. Completar información faltante manualmente
        3. Marcar trazabilidad de origen manual
        4. Persistir usando el repositorio estándar

        Args:
            study_data: Diccionario con datos del estudio
            user: Usuario que agrega el estudio (opcional)

        Returns:
            Study: Entidad de dominio creada/persistida

        Raises:
            ValueError: Si faltan campos requeridos
            Exception: Si falla la persistencia
        """
        logger.info(f"[MANUAL] Adding manual study: {study_data.get('title', 'Unknown title')}")

        try:
            # Validar campos mínimos requeridos
            if not study_data.get("title") or not study_data.get("link"):
                raise ValueError("Title and link are required for manual study")

            # 1. Crear estudio usando el factory del dominio (solo campos básicos)
            study = Study.create_discovered(
                title=study_data["title"],
                link=study_data["link"],
                source="Manual",  # Origen explícito
                doi=study_data.get("doi"),
            )

            # 2. Agregar metadatos adicionales si están presentes
            if study_data.get("year"):
                study.year = study_data["year"]
            if study_data.get("authors"):
                study.authors = study_data["authors"]
            if study_data.get("abstract"):
                study.abstract = study_data["abstract"]
            if study_data.get("journal"):
                study.journal = study_data["journal"]
            if study_data.get("keywords"):
                study.keywords = study_data["keywords"]
            if study_data.get("is_open_access") is not None:
                study.is_open_access = study_data["is_open_access"]
            if study_data.get("pdf_url"):
                study.pdf_url = study_data["pdf_url"]

            # 3. Marcar trazabilidad de origen manual
            study.field_origins = {k: "manual" for k in study_data.keys()}
            study.field_origins["source"] = "manual"  # Explícito para debugging

            # 3. Persistir usando el repositorio estándar
            persisted_study = self.study_repository.save(study)

            logger.info(f"[MANUAL] Successfully added manual study: {persisted_study.id}")
            return persisted_study

        except ValueError as ve:
            logger.error(f"[MANUAL] Validation error: {ve}")
            raise
        except Exception as e:
            logger.error(f"[MANUAL] Error adding manual study: {e}", exc_info=True)
            raise

    def update_study_metadata_manually(
        self,
        study_id: str,
        updates: Dict[str, Any],
        user: Optional[User] = None
    ) -> Study:
        """
        Corrige o completa metadatos manualmente.

        Este método permite:
        1. Corregir errores en metadatos automáticamente recolectados
        2. Agregar campos faltantes (ej. año, DOI)
        3. Sobreescribir información incorrecta
        4. Marcar trazabilidad de qué fue modificado manualmente

        Args:
            study_id: UUID del estudio a modificar
            updates: Diccionario con campos a actualizar
            user: Usuario que hace la corrección (opcional)

        Returns:
            Study: Entidad actualizada

        Raises:
            ValueError: Si no se encuentra el estudio
            Exception: Si falla la actualización
        """
        logger.info(f"[MANUAL] Updating metadata for study: {study_id}")

        try:
            # 1. Buscar estudio existente
            study = self.study_repository.find_by_id(study_id)
            if not study:
                raise ValueError(f"Study {study_id} not found")

            # 2. Aplicar actualizaciones
            for field, value in updates.items():
                if hasattr(study, field):
                    setattr(study, field, value)
                    # Marcar trazabilidad de qué campo fue modificado manualmente
                    if not hasattr(study, 'field_origins'):
                        study.field_origins = {}
                    study.field_origins[field] = "manual"

            # 3. Validar campos críticos si se actualizan
            if "doi" in updates and updates["doi"]:
                if not self._validate_doi(updates["doi"]):
                    logger.warning(f"[MANUAL] Invalid DOI format: {updates['doi']}")

            # 4. Re-validar estado de consolidación (opcional, podría llamar a servicio)
            # study.consolidation_status = self._validate_consolidation_status(study)
            # Por ahora, marcamos como "manual_review"
            study.consolidation_status = "manual_review"

            # 5. Persistir cambios
            updated_study = self.study_repository.save(study)

            logger.info(f"[MANUAL] Successfully updated study: {study_id}")
            return updated_study

        except ValueError as ve:
            logger.error(f"[MANUAL] Study not found: {ve}")
            raise
        except Exception as e:
            logger.error(f"[MANUAL] Error updating study metadata: {e}", exc_info=True)
            raise

    def upload_study_pdf(self, study_id: str, file_obj, filename: str, user: Optional[User] = None) -> Study:
        """
        Subir PDF manualmente para un estudio.

        Args:
            study_id: ID del estudio
            file_obj: Objeto archivo subido
            filename: Nombre del archivo
            user: Usuario que sube el archivo

        Returns:
            Study con PDF actualizado

        Raises:
            RuntimeError: Si el servicio de upload no está configurado
        """
        logger.info(f"[MANUAL] Uploading PDF for study {study_id}")

        if self.manual_upload_service is None:
            raise RuntimeError(
                "Manual upload service not configured. "
                "Container must inject manual_upload_service in __init__."
            )

        return self.manual_upload_service.upload_pdf_for_study(
            study_id=study_id,
            uploaded_file=file_obj
        )
        """
        Sube un PDF manual para un estudio.

        Este método DELEGA la responsabilidad completa al servicio especializado
        ManualUploadAppService, que sabe manejar:
        - Validación de archivos PDF
        - Almacenamiento en disco
        - Actualización de metadatos del estudio
        - Trazabilidad completa del origen manual

        Args:
            study_id: UUID del estudio a actualizar
            file_obj: Archivo PDF subido (InMemoryUploadedFile, File, etc.)
            filename: Nombre original del archivo
            user: Usuario que realiza la subida (opcional)

        Returns:
            Study: Entidad actualizada con la ruta del PDF y metadatos

        Raises:
            ValueError: Si no se encuentra el estudio o parámetros inválidos
            Exception: Si falla la subida (se delega al servicio especializado)
        """
        logger.info(f"[MANUAL] Delegating PDF upload for study: {study_id}, file: {filename}")

        try:
            # 1. Obtener el servicio especializado del container
            from apps.acquisition.container import Container
            manual_upload_app_service = Container.get_manual_upload_app_service()

            # 2. Validar que el servicio esté disponible
            if manual_upload_app_service is None:
                raise RuntimeError("Manual upload service not available in container")

            # 3. DELEGAR COMPLETAMENTE la responsabilidad
            # El servicio sabe: validación de PDF, storage, actualización BD, etc.
            updated_study = manual_upload_app_service.upload_pdf_for_study(
                study_id=study_id,
                uploaded_file=file_obj,
                filename=filename,
                user=user
            )

            logger.info(f"[MANUAL] PDF upload delegated successfully: {study_id}")
            return updated_study

        except ValueError as ve:
            logger.error(f"[MANUAL] Validation error: {ve}")
            raise
        except Exception as e:
            logger.error(f"[MANUAL] Error delegating PDF upload: {e}", exc_info=True)
            raise

    # ==========================================================================
    # HELPER METHODS (Mantenimiento y Validación)
    # ==========================================================================

    def _validate_doi(self, doi: str) -> bool:
        """Validar formato básico de DOI."""
        if not doi:
            return False

        # Validación básica de formato DOI
        import re
        doi_pattern = r'^(10\.\d{4,}/.*)|(doi:10\.\d{4,}/.*)$'
        return bool(re.match(doi_pattern, doi.strip()))

    def _validate_consolidation_status(self, study: Study) -> str:
        """
        Validar estado de consolidación de metadatos.

        En un sistema completo, esto llamaría a un ConsolidationService,
        pero por ahora hacemos una validación básica.
        """
        required_fields = ["title", "authors", "year"]
        missing_fields = []

        for field in required_fields:
            value = getattr(study, field, None)
            if not value:
                missing_fields.append(field)

        if missing_fields:
            logger.warning(f"[VALIDATION] Missing required fields: {missing_fields}")
            return "incomplete"

        # Si tiene DOI, validar formato
        if study.doi and not self._validate_doi(study.doi):
            return "invalid_doi"

        return "complete"
