"""
AlternativeSourceFinder - Implementación STUB de IAlternativeSourceFinder.

Por ahora es un stub que devuelve None.
En el futuro se implementará búsqueda en repositorios legales:
- arXiv
- CORE
- PubMed Central
- Repositorios institucionales
- Preprints

NO incluye fuentes de dudosa procedencia.
"""

import logging
from typing import Optional

from apps.acquisition.shared.domain.entities.study import Study

logger = logging.getLogger(__name__)


class AlternativeSourceFinder:
    """
    Implementación STUB del contrato IAlternativeSourceFinder.

    ESTADO ACTUAL: Stub vacío que devuelve None.
    FUTURO: Búsqueda en repositorios legales (arXiv, CORE, PMC, etc.)

    Uso:
        finder = AlternativeSourceFinder()
        pdf_path = finder.find_and_download(study)  # Siempre None por ahora
    """

    def __init__(self):
        """Inicializar el finder de fuentes alternativas."""
        logger.info("AlternativeSourceFinder inicializado (STUB)")

    def find_and_download(self, study: Study) -> Optional[str]:
        """
        Implementación STUB del contrato IAlternativeSourceFinder.

        Buscar y descargar PDF desde fuentes alternativas legales.

        IMPLEMENTACIÓN ACTUAL: Stub que siempre devuelve None.

        Args:
            study: Estudio del que buscar PDF alternativo

        Returns:
            None (stub vacío por ahora)

        TODO (Futuro):
            1. Buscar en arXiv si el título/autores coinciden
            2. Buscar en CORE (repositorios agregados)
            3. Buscar en PubMed Central si es biomedicina
            4. Buscar en repositorios institucionales conocidos
            5. Buscar en preprint servers (bioRxiv, medRxiv, etc.)
        """
        logger.debug(f"AlternativeSourceFinder.find_and_download llamado para {study.id} (stub, retorna None)")

        # TODO: Implementar búsqueda real cuando sea necesario
        # Por ahora, solo retornamos None para que el flujo continúe

        return None

    # Métodos futuros (comentados para referencia)

    # def _search_arxiv(self, study: Study) -> Optional[str]:
    #     """Buscar en arXiv por título/autores."""
    #     pass

    # def _search_core(self, study: Study) -> Optional[str]:
    #     """Buscar en CORE (repositorios agregados)."""
    #     pass

    # def _search_pmc(self, study: Study) -> Optional[str]:
    #     """Buscar en PubMed Central."""
    #     pass

    # def _search_institutional_repos(self, study: Study) -> Optional[str]:
    #     """Buscar en repositorios institucionales conocidos."""
    #     pass
