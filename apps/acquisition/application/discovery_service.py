"""
Discovery service for executing discovery operations.

ORQUESTACIÓN FASE 4 (con trazabilidad completa):
1. Calcular fuentes ejecutables y rastrear no ejecutadas con razones
2. Consultar cada fuente ejecutable usando su conector
3. Consolidar estudios de todas las fuentes
4. DEDUPLICAR usando Deduplicator del dominio
5. Construir summary completo: id_estrategia, total_por_fuente, total_bruto, total_unicos, no_ejecutadas, resultado
6. Definir resultado: "complete" si no_ejecutadas está vacío, "partial" en caso contrario
"""
from typing import Dict, List

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

    def __init__(self, connectors: Dict[str, IAcademicConnector]):
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
        supported_sources: list
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
        # 0. VALIDACIONES TEMPRANAS (FASE 5: robustez de entradas)

        # Validar strategy_id no vacío
        if not strategy_id or not strategy_id.strip():
            raise ValueError("strategy_id no puede estar vacío")

        # Validar que translation_statuses solo contenga fuentes soportadas
        # (advertencia, no excepción - ser tolerante)
        if translation_statuses:
            unsupported = set(translation_statuses.keys()) - set(SUPPORTED_SOURCES)
            if unsupported:
                # Filtrar silenciosamente fuentes no soportadas
                translation_statuses = {
                    k: v for k, v in translation_statuses.items()
                    if k in SUPPORTED_SOURCES
                }

        # 1. Calcular fuentes ejecutables y rastrear no ejecutadas con razones
        # Intersección: supported_sources ∩ connectors.keys() ∩ status=="ready" ∩ query no vacía
        executable_sources: List[str] = []
        no_ejecutadas: Dict[str, str] = {}

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

        # 2. Consultar cada fuente ejecutable
        all_studies: List[Study] = []
        total_por_fuente: Dict[str, int] = {}

        for source in executable_sources:
            connector = self.connectors[source]
            query = translation_statuses[source].get("query", "")

            # Consultar fuente
            studies = list(connector.search(query))

            # Acumular
            all_studies.extend(studies)
            total_por_fuente[source] = len(studies)

        # 3. Calcular total_bruto
        total_bruto = sum(total_por_fuente.values())

        # 4. DEDUPLICAR (FASE 3)
        unique_studies = self.deduplicator.deduplicate(all_studies)

        # 5. Determinar resultado (complete | partial) - FASE 4: basado en no_ejecutadas
        # "complete" solo si no_ejecutadas está vacío (todas las fuentes ejecutadas)
        # "partial" si hay al menos una fuente no ejecutada
        resultado = DISCOVERY_RESULT_COMPLETE if not no_ejecutadas else DISCOVERY_RESULT_PARTIAL

        # 6. Construir resumen completo (FASE 4: con no_ejecutadas)
        summary = {
            "id_estrategia": strategy_id,
            "resultado": resultado,
            "total_bruto": total_bruto,
            "total_unicos": len(unique_studies),
            "total_por_fuente": total_por_fuente,
            "no_ejecutadas": no_ejecutadas,
        }

        # 7. Retornar resultado (CON deduplicación y trazabilidad completa)
        return DiscoveryResult(studies=unique_studies, summary=summary)
