"""
ChainedOpenAccessChecker - Orquestador de verificación OA usando Chain of Responsibility.

Este módulo actúa como wrapper/facade sobre la cadena de checkers para:
- Respetar el hint de OA existente en el Study (evitar llamadas innecesarias)
- Enriquecer el Study con la información encontrada (pdf_url, is_open_access)
- Optimizar llamadas a APIs cuando el estudio viene de una fuente específica

Patrón: Facade sobre Chain of Responsibility
- Recibe el primer eslabón de la cadena
- Añade lógica de negocio antes de delegar a la cadena

Nota: Este archivo se renombrará internamente pero mantiene el nombre
CompositeOpenAccessChecker para compatibilidad hacia atrás.
"""
from typing import Optional, List
import logging

from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.shared.domain.value_objects.doi import DOI
from apps.acquisition.downloads.domain.interfaces import (
    BaseOpenAccessChecker,
    OpenAccessResult,
)

logger = logging.getLogger(__name__)


class ChainedOpenAccessChecker:
    """
    Orquestador de verificación de OA que envuelve una cadena de checkers.
    
    Este componente es un Facade que:
    1. Respeta el hint existente (study.is_open_access == True)
    2. Delega la verificación a la cadena de checkers
    3. Enriquece el Study con la información encontrada
    4. Optimiza llamadas cuando el estudio viene de fuentes específicas
    
    Uso:
        # La cadena ya viene configurada desde el Container
        chain_head = unpaywall  # -> crossref -> scopus -> None
        
        orchestrator = ChainedOpenAccessChecker(
            checker_chain=chain_head,
            skip_sources=["Scopus"]
        )
        
        result = orchestrator.check_access(doi, study)
    """

    def __init__(
        self,
        checker_chain: BaseOpenAccessChecker,
        skip_sources: Optional[List[str]] = None,
    ):
        """
        Inicializar el orquestador.

        Args:
            checker_chain: Primer eslabón de la cadena de checkers (ya encadenados)
            skip_sources: Lista de fuentes para las cuales NO consultar la cadena completa
                         (ej. ['Scopus'] para no re-consultar Scopus API si el estudio
                         ya viene de Scopus)
        """
        self.checker_chain = checker_chain
        self.skip_sources = skip_sources or []

    def check_access(self, doi: DOI, study: Optional[Study] = None) -> OpenAccessResult:
        """
        Verificar Open Access usando la cadena de checkers.

        Args:
            doi: DOI a consultar
            study: Study opcional para enriquecer con información OA

        Returns:
            OpenAccessResult con la información encontrada
        """
        # 1. Respetar hint existente
        if study and study.is_open_access is True:
            logger.debug(f"⚡ Estudio {doi.value if doi else 'N/A'} ya marcado como OA")
            return OpenAccessResult(
                is_oa=True,
                pdf_url=getattr(study, 'pdf_url', None),
                source="Hint",
            )

        # 2. Validación básica
        if not doi or not doi.value:
            return OpenAccessResult.not_found(source="InvalidDOI")

        # 3. Verificar si debemos saltar por fuente del estudio
        if study and self._should_skip(study):
            source_name = getattr(study.source, 'name', str(study.source)) if study.source else 'Unknown'
            logger.info(
                f"⚡ Saltando verificación OA para estudio de {source_name} "
                f"(ya consultado en Discovery)"
            )
            return OpenAccessResult.not_found(source="Skipped")

        # 4. Delegar a la cadena
        result = self.checker_chain.check_access(doi)

        # 5. Enriquecer el Study si encontramos OA
        if study and result.is_oa:
            study.is_open_access = True
            if result.pdf_url:
                study.pdf_url = result.pdf_url
            logger.info(f"✅ OA encontrado para {doi.value} vía {result.source}")

        return result

    def is_open_access(self, doi: DOI, study: Optional[Study] = None) -> bool:
        """
        Wrapper para compatibilidad con IOpenAccessChecker Protocol.

        Args:
            doi: DOI a consultar
            study: Study opcional

        Returns:
            True si es Open Access, False en caso contrario
        """
        result = self.check_access(doi, study)
        return result.is_oa

    def get_oa_info(self, doi: DOI) -> dict:
        """
        Wrapper para compatibilidad con código existente que espera Dict.

        Args:
            doi: DOI a consultar

        Returns:
            Diccionario con información OA
        """
        result = self.check_access(doi, study=None)
        return {
            "is_oa": result.is_oa,
            "pdf_url": result.pdf_url,
            "landing_url": result.landing_url,
            "source": result.source,
            "oa_type": result.oa_type,
            "license": result.license,
            "version": result.version,
        }

    def _should_skip(self, study: Study) -> bool:
        """
        Determinar si debemos saltar la verificación para este estudio.

        Útil para evitar consultar Scopus API si el estudio ya viene de Scopus.
        """
        if not study.source:
            return False
        
        source_name = getattr(study.source, 'name', None)
        if source_name is None:
            source_name = str(study.source)
        
        return source_name in self.skip_sources


# Alias para compatibilidad hacia atrás
CompositeOpenAccessChecker = ChainedOpenAccessChecker
