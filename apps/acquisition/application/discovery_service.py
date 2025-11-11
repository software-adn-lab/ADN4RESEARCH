"""
Discovery service for executing discovery operations.

ORQUESTACIÓN:
1. Filtrar fuentes con translation_statuses "ready"
2. Consultar cada fuente ready usando su conector
3. Consolidar estudios de todas las fuentes
4. Deduplicar usando Deduplicator del dominio
5. Construir resumen con estadísticas
"""
from typing import Dict, List

from apps.acquisition.domain.interfaces.i_academic_connector import IAcademicConnector
from apps.acquisition.domain.entities.discovery_result import DiscoveryResult
from apps.acquisition.domain.entities.study import Study
from apps.acquisition.domain.services.deduplication.deduplicator import Deduplicator
from apps.acquisition.domain.constants import (
    TRANSLATION_STATUS_READY,
    DISCOVERY_RESULT_COMPLETE,
    DISCOVERY_RESULT_PARTIAL
)


class DiscoveryService:
    """
    Application service for orchestrating the discovery process.

    Responsabilidades:
    1. Filtrar fuentes con traducción "ready"
    2. Consultar cada fuente usando IAcademicConnector
    3. Consolidar y deduplicar resultados
    4. Construir resumen de ejecución
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
        Execute the discovery process.

        Flujo:
        1. Identificar fuentes ready (tienen query traducida)
        2. Consultar cada fuente ready con su conector
        3. Consolidar estudios de todas las fuentes
        4. Deduplicar usando DOI > título
        5. Construir resumen con:
           - id_estrategia
           - resultado: "complete" (todas ready) | "partial" (alguna not_supported)
           - total_bruto: suma de estudios por fuente
           - total_unicos: después de deduplicación
           - total_por_fuente: {fuente: count}

        Args:
            strategy_id: ID of the search strategy to use
            translation_statuses: Dictionary with translation status for each source
                                  Format: {source: {"status": str, "query": Optional[str]}}
            supported_sources: List of sources to query

        Returns:
            DiscoveryResult with studies and summary

        Ejemplos:
            >>> # Ambas fuentes ready
            >>> statuses = {
            ...     "Scopus": {"status": "ready", "query": "MOCK_QUERY"},
            ...     "IEEE Xplore": {"status": "ready", "query": "MOCK_QUERY"}
            ... }
            >>> result = service.execute("norm-001", statuses, ["Scopus", "IEEE Xplore"])
            >>> result.summary["resultado"]
            'complete'

            >>> # Una fuente not_supported
            >>> statuses = {
            ...     "Scopus": {"status": "ready", "query": "MOCK_QUERY"},
            ...     "IEEE Xplore": {"status": "not_supported", "query": None}
            ... }
            >>> result = service.execute("norm-002", statuses, ["Scopus", "IEEE Xplore"])
            >>> result.summary["resultado"]
            'partial'
        """
        # 1. Identificar fuentes ready
        ready_sources = [
            source for source in supported_sources
            if (source in translation_statuses and
                translation_statuses[source].get("status") == TRANSLATION_STATUS_READY)
        ]

        # 2. Consultar cada fuente ready
        all_studies: List[Study] = []
        total_por_fuente: Dict[str, int] = {}

        for source in ready_sources:
            if source not in self.connectors:
                # Sin conector disponible (no debería pasar en producción)
                continue

            connector = self.connectors[source]
            query = translation_statuses[source].get("query", "")

            # Consultar fuente
            studies = list(connector.search(query))

            # Acumular
            all_studies.extend(studies)
            total_por_fuente[source] = len(studies)

        # 3. Deduplicar
        unique_studies = self.deduplicator.deduplicate(all_studies)

        # 4. Calcular total_bruto
        total_bruto = sum(total_por_fuente.values())

        # 5. Determinar resultado (complete | partial)
        all_ready = all(
            translation_statuses.get(src, {}).get("status") == TRANSLATION_STATUS_READY
            for src in supported_sources
        )
        resultado = DISCOVERY_RESULT_COMPLETE if all_ready else DISCOVERY_RESULT_PARTIAL

        # 6. Construir resumen
        summary = {
            "id_estrategia": strategy_id,
            "resultado": resultado,
            "total_bruto": total_bruto,
            "total_unicos": len(unique_studies),
            "total_por_fuente": total_por_fuente,
        }

        # 7. Retornar resultado
        return DiscoveryResult(studies=unique_studies, summary=summary)
