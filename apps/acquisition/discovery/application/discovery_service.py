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

OPTIMIZACIÓN:
- Ejecución PARALELA de conectores usando ThreadPoolExecutor
- Las búsquedas son I/O bound (espera de red), los threads funcionan perfecto
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
        supported_sources: list[str],
        max_results_per_source: int = 25
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
            max_results_per_source: Maximum results to fetch from each source (default: 25)

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
            executable_sources, sane_statuses, no_ejecutadas, max_results_per_source
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

    def _normalize_status(self, raw_status: str) -> str:
        """
        Normaliza el status de traducción para tolerar variaciones.

        El Feature 1 retorna "Done" cuando la traducción fue exitosa, mientras
        que Discovery espera "ready". Este método los mapea al mismo valor
        para evitar que el pipeline se detenga aunque las traducciones estén
        listas.
        """
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

            status = self._normalize_status(translation_statuses[source].get("status"))
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
        no_ejecutadas: dict[str, str],
        max_results: int = 25
    ) -> tuple[list[Study], dict[str, int]]:
        """
        Consultar cada fuente ejecutable EN PARALELO con manejo robusto de excepciones.

        OPTIMIZACIÓN: Usa ThreadPoolExecutor para ejecutar todas las búsquedas
        simultáneamente. El tiempo total = max(tiempo_fuente1, tiempo_fuente2, ...)
        en lugar de suma de tiempos.

        CRÍTICO PARA PRODUCCIÓN: Si una fuente falla (timeout, error 500, etc.),
        NO detener todo el proceso. Registrar el error y continuar con las demás.

        Args:
            executable_sources: Fuentes a consultar
            translation_statuses: Estados de traducción
            no_ejecutadas: Dict para registrar fuentes que fallen (se modifica in-place)
            max_results: Máximo de resultados por fuente

        Returns:
            (all_studies, total_por_fuente)
        """
        all_studies: list[Study] = []
        total_por_fuente: dict[str, int] = {}

        if not executable_sources:
            return all_studies, total_por_fuente

        # Ejecutar búsquedas EN PARALELO
        with ThreadPoolExecutor(max_workers=len(executable_sources)) as executor:
            # Crear futures para cada fuente
            future_to_source = {
                executor.submit(
                    self._fetch_single_source,
                    source,
                    translation_statuses[source].get("query", ""),
                    max_results
                ): source
                for source in executable_sources
            }

            # Recolectar resultados conforme terminan
            for future in as_completed(future_to_source):
                source = future_to_source[future]

                try:
                    converted = future.result()

                    # Éxito: acumular resultados
                    all_studies.extend(converted)
                    total_por_fuente[source] = len(converted)

                    logger.info(f"✓ {source}: {len(converted)} estudios obtenidos")

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

    def _fetch_single_source(
        self,
        source: str,
        query: str,
        max_results: int
    ) -> list[Study]:
        """
        Consulta una fuente individual y convierte resultados a Study.

        Args:
            source: Nombre de la fuente
            query: Query de búsqueda
            max_results: Máximo de resultados

        Returns:
            Lista de Study convertidos

        Raises:
            Exception: Si la búsqueda falla
        """
        connector = self.connectors[source]

        # PUNTO CRÍTICO: Aquí es donde puede fallar en producción
        raw_results = list(connector.search(query, max_results=max_results))

        # Convertir resultados crudos (dicts) a entidades Study del dominio,
        # respetando también conectores que ya retornan Study (mocks).
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

                # Enriquecer con metadatos si existen
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
