"""
Discovery service for executing discovery operations.

ORQUESTACIÓN (Refactorizada para producción):
1. Validar entradas (fail-fast)
2. Sanear translation_statuses (tolerancia)
3. Calcular fuentes ejecutables y rastrear no ejecutadas con razones
4. Consultar cada fuente ejecutable usando su conector (con manejo de excepciones)
5. Consolidar estudios de todas las fuentes
6. DEDUPLICAR usando Deduplicator del dominio
7. Construir summary completo: id_estrategia, total_por_fuente, total_bruto, total_unicos, no_ejecutadas, resultado
8. Definir resultado: "complete" si no_ejecutadas está vacío, "partial" en caso contrario
"""
import logging

from apps.acquisition.domain.interfaces.i_academic_connector import IAcademicConnector
from apps.acquisition.domain.entities.discovery_result import DiscoveryResult
from apps.acquisition.domain.entities.study import Study
from apps.acquisition.domain.services.deduplication.deduplicator import Deduplicator
from apps.acquisition.domain.constants import (
    SUPPORTED_SOURCES,
    TRANSLATION_STATUS_READY,
    DISCOVERY_RESULT_COMPLETE,
    DISCOVERY_RESULT_PARTIAL
)

logger = logging.getLogger(__name__)


class DiscoveryService:
    """
    Application service for orchestrating the discovery process.

    Responsabilidades FASE 4 (con trazabilidad completa):
    1. Calcular fuentes ejecutables y rastrear no ejecutadas con razones
    2. Consultar cada fuente usando IAcademicConnector
    3. Consolidar resultados de todas las fuentes
    4. Deduplicar usando Deduplicator del dominio
    5. Construir resumen de ejecución con trazabilidad completa
    """

    def __init__(self, connectors: dict[str, IAcademicConnector]):
        """
        Initialize the discovery service.

        Args:
            connectors: Dictionary mapping source names to their connector implementations
        """
        self.connectors = connectors
        self.deduplicator = Deduplicator()

    def execute(
        self,
        strategy_id: str,
        translation_statuses: dict,
        supported_sources: list[str]
    ) -> DiscoveryResult:
        """
        Execute the discovery process (FASE 4: con trazabilidad completa).

        Flujo:
        1. Calcular fuentes ejecutables y rastrear no ejecutadas con razones:
           Ejecutable si:
           - Está en supported_sources
           - Tiene conector inyectado (en self.connectors)
           - Tiene status "ready" en translation_statuses
           - Tiene query no vacía
           Razones de no ejecución:
           - "not_supported": status != "ready"
           - "missing_query": status == "ready" pero query vacía
           - "missing_connector": no hay conector inyectado
        2. Consultar cada fuente ejecutable con su conector
        3. Consolidar estudios de todas las fuentes
        4. DEDUPLICAR usando Deduplicator (DOI > título)
        5. Construir summary completo:
           - id_estrategia
           - resultado: "complete" (no_ejecutadas vacío) | "partial" (hay no_ejecutadas)
           - total_bruto: suma de estudios por fuente
           - total_unicos: después de deduplicación
           - total_por_fuente: {fuente: count}
           - no_ejecutadas: {fuente: razón}

        Args:
            strategy_id: ID of the search strategy to use
            translation_statuses: Dictionary with translation status for each source
                                  Format: {source: {"status": str, "query": Optional[str]}}
            supported_sources: List of sources to query

        Returns:
            DiscoveryResult with unique studies (deduplicados) and summary completo con trazabilidad

        Ejemplos:
            >>> # Ambas fuentes ejecutables
            >>> statuses = {
            ...     "Scopus": {"status": "ready", "query": "MOCK_QUERY"},
            ...     "IEEE Xplore": {"status": "ready", "query": "MOCK_QUERY"}
            ... }
            >>> result = service.execute("norm-001", statuses, ["Scopus", "IEEE Xplore"])
            >>> result.summary["resultado"]
            'complete'
            >>> result.summary["no_ejecutadas"]
            {}
            >>> result.summary["total_bruto"]
            6
            >>> result.summary["total_unicos"]
            4

            >>> # Una fuente not_supported
            >>> statuses = {
            ...     "Scopus": {"status": "ready", "query": "MOCK_QUERY"},
            ...     "IEEE Xplore": {"status": "not_supported", "query": None}
            ... }
            >>> result = service.execute("norm-002", statuses, ["Scopus", "IEEE Xplore"])
            >>> result.summary["resultado"]
            'partial'
            >>> result.summary["no_ejecutadas"]
            {"IEEE Xplore": "not_supported"}
            >>> result.summary["total_bruto"]
            3
            >>> result.summary["total_unicos"]
            3
        """
        # 1. Validaciones tempranas (fail-fast)
        self._validate_inputs(strategy_id)

        # 2. Sanear translation_statuses (tolerancia)
        sane_statuses = self._sanitize_statuses(translation_statuses)

        # 3. Determinar plan de ejecución (fuentes ejecutables vs no ejecutables)
        executable_sources, no_ejecutadas = self._determine_execution_plan(
            supported_sources, sane_statuses
        )

        # 4. Consultar fuentes ejecutables (con manejo robusto de excepciones)
        all_studies, total_por_fuente = self._fetch_studies(
            executable_sources, sane_statuses, no_ejecutadas
        )

        # 5. Deduplicar (dominio)
        unique_studies = self.deduplicator.deduplicate(all_studies)

        # 6. Construir resultado final
        return self._build_result(
            strategy_id, unique_studies, total_por_fuente, no_ejecutadas
        )

    # ========================================================================
    # MÉTODOS PRIVADOS (Extract Method Pattern)
    # ========================================================================

    def _validate_inputs(self, strategy_id: str) -> None:
        """
        Validar entradas críticas (fail-fast).

        Args:
            strategy_id: ID de la estrategia

        Raises:
            ValueError: Si strategy_id está vacío
        """
        if not strategy_id or not strategy_id.strip():
            raise ValueError("strategy_id no puede estar vacío")

    def _sanitize_statuses(self, translation_statuses: dict) -> dict:
        """
        Filtrar fuentes no soportadas de translation_statuses.

        Ser tolerante: no lanzar excepción, solo advertir y filtrar.

        Args:
            translation_statuses: Estados de traducción por fuente

        Returns:
            dict con solo fuentes soportadas
        """
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

    def _determine_execution_plan(
        self,
        supported_sources: list[str],
        translation_statuses: dict
    ) -> tuple[list[str], dict[str, str]]:
        """
        Calcular fuentes ejecutables y rastrear no ejecutadas con razones.

        Una fuente es ejecutable si:
        - Tiene conector inyectado
        - Tiene status "ready" en translation_statuses
        - Tiene query no vacía

        Args:
            supported_sources: Lista de fuentes soportadas
            translation_statuses: Estados de traducción por fuente

        Returns:
            (executable_sources, no_ejecutadas)
        """
        executable_sources: list[str] = []
        no_ejecutadas: dict[str, str] = {}

        for source in supported_sources:
            # Verificar que tiene conector
            if source not in self.connectors:
                no_ejecutadas[source] = "missing_connector"
                continue

            # Verificar que tiene translation status "ready"
            if source not in translation_statuses:
                no_ejecutadas[source] = "not_supported"
                continue

            status = translation_statuses[source].get("status")
            if status != TRANSLATION_STATUS_READY:
                no_ejecutadas[source] = "not_supported"
                continue

            # Verificar que tiene query no vacía
            query = translation_statuses[source].get("query", "")
            if not query or not query.strip():
                no_ejecutadas[source] = "missing_query"
                continue

            # Si pasa todas las condiciones, es ejecutable
            executable_sources.append(source)

        return executable_sources, no_ejecutadas

    def _fetch_studies(
        self,
        executable_sources: list[str],
        translation_statuses: dict,
        no_ejecutadas: dict[str, str]
    ) -> tuple[list[Study], dict[str, int]]:
        """
        Consultar cada fuente ejecutable con manejo robusto de excepciones.

        CRÍTICO PARA PRODUCCIÓN: Si una fuente falla (timeout, error 500, etc.),
        NO detener todo el proceso. Registrar el error y continuar con las demás.

        Args:
            executable_sources: Fuentes a consultar
            translation_statuses: Estados de traducción
            no_ejecutadas: Dict para registrar fuentes que fallen (se modifica in-place)

        Returns:
            (all_studies, total_por_fuente)
        """
        all_studies: list[Study] = []
        total_por_fuente: dict[str, int] = {}

        for source in executable_sources:
            connector = self.connectors[source]
            query = translation_statuses[source].get("query", "")

            try:
                # PUNTO CRÍTICO: Aquí es donde puede fallar en producción
                studies = list(connector.search(query))

                # Éxito: acumular resultados
                all_studies.extend(studies)
                total_por_fuente[source] = len(studies)

                logger.info(f"✓ {source}: {len(studies)} estudios obtenidos")

            except Exception as e:
                # NO detener todo el proceso por una fuente caída
                error_msg = f"connection_error: {type(e).__name__}: {str(e)}"
                no_ejecutadas[source] = error_msg

                logger.error(
                    f"✗ {source}: Error al consultar conector. "
                    f"Continuando con otras fuentes. Error: {e}",
                    exc_info=True
                )

        return all_studies, total_por_fuente

    def _build_result(
        self,
        strategy_id: str,
        unique_studies: list[Study],
        total_por_fuente: dict[str, int],
        no_ejecutadas: dict[str, str]
    ) -> DiscoveryResult:
        """
        Construir el resultado final con summary completo.

        Args:
            strategy_id: ID de la estrategia
            unique_studies: Estudios después de deduplicación
            total_por_fuente: Conteo bruto por fuente
            no_ejecutadas: Fuentes no ejecutadas con razones

        Returns:
            DiscoveryResult con studies y summary
        """
        total_bruto = sum(total_por_fuente.values())

        # Determinar resultado (complete | partial)
        resultado = DISCOVERY_RESULT_COMPLETE if not no_ejecutadas else DISCOVERY_RESULT_PARTIAL

        summary = {
            "id_estrategia": strategy_id,
            "resultado": resultado,
            "total_bruto": total_bruto,
            "total_unicos": len(unique_studies),
            "total_por_fuente": total_por_fuente,
            "no_ejecutadas": no_ejecutadas,
        }

        return DiscoveryResult(studies=unique_studies, summary=summary)
