"""
Discovery service for executing discovery operations.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from apps.acquisition.discovery.domain.interfaces.i_academic_connector import IAcademicConnector
from apps.acquisition.discovery.domain.entities.discovery_result import DiscoveryResult
from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.discovery.domain.services.deduplicator import Deduplicator
from apps.acquisition.shared.domain.constants import (
    SUPPORTED_SOURCES,
    TRANSLATION_STATUS_READY,
    DISCOVERY_RESULT_COMPLETE,
    DISCOVERY_RESULT_PARTIAL
)

logger = logging.getLogger(__name__)


class DiscoveryService:
    """
    Application service for orchestrating the discovery process.
    """

    def __init__(self, connectors: dict[str, IAcademicConnector], repository=None):
        """
        Initialize the discovery service.

        Args:
            connectors: Dictionary mapping source names to their connector implementations
            repository: Optional IStudyRepository for persistence (None = no persistence)
        """
        self.connectors = connectors
        self.repository = repository
        self.deduplicator = Deduplicator()

    def execute(
        self,
        strategy_id: str,
        translation_statuses: dict,
        supported_sources: list[str],
        max_results_per_source: int = 25
    ) -> DiscoveryResult:
        """
        Execute the discovery process.

        Args:
            strategy_id: ID of the search strategy to use
            translation_statuses: Dictionary with translation status for each source
            supported_sources: List of sources to query
            max_results_per_source: Maximum results to fetch from each source

        Returns:
            DiscoveryResult with unique studies and summary
        """
        self._validate_inputs(strategy_id)
        sane_statuses = self._sanitize_statuses(translation_statuses)
        executable_sources, no_ejecutadas = self._determine_execution_plan(
            supported_sources, sane_statuses
        )
        all_studies, total_por_fuente, studies_by_source = self._fetch_studies(
            executable_sources, sane_statuses, no_ejecutadas, max_results_per_source
        )
        unique_studies = self.deduplicator.deduplicate(all_studies)

        # Persistencia opcional: Si hay repositorio inyectado, guardar estudios
        if self.repository and unique_studies:
            logger.info(f"Persistiendo {len(unique_studies)} estudios en base de datos...")
            unique_studies = self.repository.save_batch(unique_studies)
            logger.info("Persistencia completada")

        return self._build_result(
            strategy_id, unique_studies, total_por_fuente, no_ejecutadas, studies_by_source
        )

    def _validate_inputs(self, strategy_id: str) -> None:
        """Validar entradas críticas."""
        if not strategy_id or not strategy_id.strip():
            raise ValueError("strategy_id no puede estar vacío")

    def _sanitize_statuses(self, translation_statuses: dict) -> dict:
        """Filtrar fuentes no soportadas de translation_statuses."""
        if not translation_statuses:
            return {}

        unsupported = set(translation_statuses.keys()) - set(SUPPORTED_SOURCES)
        if unsupported:
            logger.warning(
                f"Fuentes no soportadas ignoradas: {unsupported}. "
                f"Soportadas: {SUPPORTED_SOURCES}"
            )
            return {
                k: v for k, v in translation_statuses.items()
                if k in SUPPORTED_SOURCES
            }

        return translation_statuses

    def _normalize_status(self, raw_status: str) -> str:
        """Normaliza el status de traducción para tolerar variaciones."""
        if not raw_status:
            return ""

        normalized = raw_status.strip().lower()
        if normalized == "done":
            return TRANSLATION_STATUS_READY

        return normalized

    def _determine_execution_plan(
        self,
        supported_sources: list[str],
        translation_statuses: dict
    ) -> tuple[list[str], dict[str, str]]:
        """Calcular fuentes ejecutables y rastrear no ejecutadas con razones."""
        executable_sources: list[str] = []
        no_ejecutadas: dict[str, str] = {}

        for source in supported_sources:
            if source not in self.connectors:
                no_ejecutadas[source] = "missing_connector"
                continue

            if source not in translation_statuses:
                no_ejecutadas[source] = "not_supported"
                continue

            status = self._normalize_status(translation_statuses[source].get("status"))
            if status != TRANSLATION_STATUS_READY:
                no_ejecutadas[source] = "not_supported"
                continue

            query = translation_statuses[source].get("query", "")
            if not query or not query.strip():
                no_ejecutadas[source] = "missing_query"
                continue

            executable_sources.append(source)

        return executable_sources, no_ejecutadas

    def _fetch_studies(
        self,
        executable_sources: list[str],
        translation_statuses: dict,
        no_ejecutadas: dict[str, str],
        max_results: int = 25
    ) -> tuple[list[Study], dict[str, int], dict[str, list[Study]]]:
        """Consultar cada fuente ejecutable en paralelo con manejo robusto de excepciones."""
        all_studies: list[Study] = []
        total_por_fuente: dict[str, int] = {}
        studies_by_source: dict[str, list[Study]] = {}

        if not executable_sources:
            return all_studies, total_por_fuente, studies_by_source

        with ThreadPoolExecutor(max_workers=len(executable_sources)) as executor:
            future_to_source = {
                executor.submit(
                    self._fetch_single_source,
                    source,
                    translation_statuses[source].get("query", ""),
                    max_results
                ): source
                for source in executable_sources
            }

            for future in as_completed(future_to_source):
                source = future_to_source[future]

                try:
                    converted = future.result()
                    all_studies.extend(converted)
                    total_por_fuente[source] = len(converted)
                    studies_by_source[source] = converted  # ← Guardar estudios por fuente
                    logger.info(f"✓ {source}: {len(converted)} estudios obtenidos")

                except Exception as e:
                    error_msg = f"connection_error: {type(e).__name__}: {str(e)}"
                    no_ejecutadas[source] = error_msg
                    logger.error(
                        f"✗ {source}: Error al consultar conector. "
                        f"Continuando con otras fuentes. Error: {e}",
                        exc_info=True
                    )

        return all_studies, total_por_fuente, studies_by_source

    def _fetch_single_source(
        self,
        source: str,
        query: str,
        max_results: int
    ) -> list[Study]:
        """Consulta una fuente individual y convierte resultados a Study."""
        connector = self.connectors[source]
        raw_results = list(connector.search(query, max_results=max_results))
        converted: list[Study] = []

        for item in raw_results:
            if isinstance(item, Study):
                converted.append(item)
                continue

            if isinstance(item, dict):
                title = item.get("title")
                link = item.get("link")
                source_name = item.get("source") or source

                if not title or not link:
                    logger.warning(
                        f"{source}: Resultado descartado por falta de title/link: {item}"
                    )
                    continue

                study = Study.create_discovered(
                    title=title,
                    link=link,
                    source=source_name,
                    doi=item.get("doi"),
                )

                if "authors" in item:
                    study.authors = item.get("authors")
                if "abstract" in item:
                    study.abstract = item.get("abstract")
                if "year" in item:
                    study.year = item.get("year")
                if "is_open_access" in item:
                    study.is_open_access = item.get("is_open_access")
                if "pdf_url" in item:
                    study.pdf_url = item.get("pdf_url")

                converted.append(study)
                continue

            logger.warning(
                f"{source}: Tipo de resultado inesperado {type(item)}, se descarta"
            )

        return converted

    def _build_result(
        self,
        strategy_id: str,
        unique_studies: list[Study],
        total_por_fuente: dict[str, int],
        no_ejecutadas: dict[str, str],
        studies_by_source: dict[str, list[Study]]
    ) -> DiscoveryResult:
        """Construir el resultado final con summary completo."""
        total_bruto = sum(total_por_fuente.values())
        resultado = DISCOVERY_RESULT_COMPLETE if not no_ejecutadas else DISCOVERY_RESULT_PARTIAL

        summary = {
            "id_estrategia": strategy_id,
            "resultado": resultado,
            "total_bruto": total_bruto,
            "total_unicos": len(unique_studies),
            "total_por_fuente": total_por_fuente,
            "no_ejecutadas": no_ejecutadas,
            "studies_by_source": studies_by_source,  # ← Agregar para orchestrator
        }

        return DiscoveryResult(studies=unique_studies, summary=summary)
