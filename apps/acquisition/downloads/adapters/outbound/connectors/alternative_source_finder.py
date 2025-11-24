"""
AlternativeSourceFinder - Búsqueda en repositorios alternativos.

ESTRATEGIA DE BÚSQUEDA (en orden):
1. LibGen (Library Genesis, zona gris) - OPT-IN ⚠️
2. Sci-Hub (último recurso, zona gris) - OPT-IN ⚠️

CONSIDERACIONES LEGALES:
- LibGen y Sci-Hub operan en zona gris legal
- DESHABILITADOS por defecto (requieren ENABLE_SCIHUB=true)
- Solo se activan con consentimiento explícito del usuario
- Para uso académico personal únicamente

ESTADO ACTUAL:
- LibGen: Implementado (deshabilitado por defecto) ⚠️
- Sci-Hub: Implementado (deshabilitado por defecto) ⚠️
"""
import logging
import os
from typing import Optional

from apps.acquisition.shared.domain.entities.study import Study
from .scihub_downloader import SciHubDownloader
from .libgen_scraper import LibGenScraper

logger = logging.getLogger(__name__)


class AlternativeSourceFinder:
    """
    Buscador de PDFs en fuentes alternativas (zona gris legal).

    Fuentes implementadas:
    1. LibGen (Library Genesis) - Repositorio de papers académicos
    2. Sci-Hub - Último recurso

    IMPORTANTE: Ambas fuentes están DESHABILITADAS por defecto.
    Solo se activan con enable_scihub=True (opt-in explícito).
    """

    def __init__(
        self,
        enable_scihub: bool = False,
        base_dir: str = "media/papers"
    ):
        """
        Args:
            enable_scihub: Si True, habilita LibGen y Sci-Hub (zona gris legal)
            base_dir: Directorio base para guardar PDFs
        """
        self.base_dir = base_dir
        self.enable_scihub = enable_scihub

        # Inicializar LibGen scraper (deshabilitado por defecto)
        self.libgen = LibGenScraper(
            enabled=enable_scihub,
            timeout=30,
            delay=3.0
        )

        # Inicializar Sci-Hub downloader (deshabilitado por defecto)
        self.scihub = SciHubDownloader(
            enabled=enable_scihub,
            base_dir=base_dir
        )

        if enable_scihub:
            logger.warning(
                "⚠️  AlternativeSourceFinder: LibGen y Sci-Hub HABILITADOS. "
                "Usar solo para investigación académica personal."
            )
        else:
            logger.info(
                "AlternativeSourceFinder inicializado "
                "(fuentes alternativas deshabilitadas)"
            )

    def find_and_download(self, study: Study) -> Optional[str]:
        """
        Busca y descarga PDF desde fuentes alternativas (zona gris legal).

        Orden de búsqueda:
        1. LibGen (Library Genesis) - Repositorio de papers académicos
        2. Sci-Hub - Último recurso

        IMPORTANTE: Ambas fuentes requieren enable_scihub=True (opt-in).

        Args:
            study: Estudio del que buscar PDF

        Returns:
            Ruta del PDF descargado o None si no se encontró
        """
        if not self.enable_scihub:
            logger.debug("[AlternativeSourceFinder] Fuentes alternativas deshabilitadas")
            return None

        if not study.doi:
            logger.debug(f"Estudio {study.id} sin DOI, saltando búsqueda alternativa")
            return None

        logger.info(f"[AlternativeSourceFinder] Buscando en LibGen/Sci-Hub para: {study.title[:50]}...")

        # ====================================================================
        # FUENTE 1: LibGen (Library Genesis)
        # ====================================================================
        try:
            result = self.libgen.search_by_doi(study.doi.value)
            if result and result.get('download_url'):
                logger.info(f"[LibGen] Enlace encontrado, descargando...")

                # Generar path para guardar
                import uuid
                from pathlib import Path
                filename = f"{uuid.uuid4()}.pdf"
                output_path = str(Path(self.base_dir) / filename)

                # Descargar
                if self.libgen.download_from_url(result['download_url'], output_path):
                    logger.info(f"✓ PDF descargado desde LibGen: {output_path}")
                    return output_path
        except Exception as e:
            logger.debug(f"[LibGen] Error: {e}")

        # ====================================================================
        # FUENTE 2: Sci-Hub (último recurso)
        # ====================================================================
        logger.info("[AlternativeSourceFinder] LibGen falló, intentando Sci-Hub...")
        pdf_path = self.scihub.download(study.doi.value)
        if pdf_path:
            logger.info(f"✓ PDF descargado desde Sci-Hub: {pdf_path}")
            return pdf_path

        logger.info("[AlternativeSourceFinder] No se encontró PDF en LibGen ni Sci-Hub")
        return None
