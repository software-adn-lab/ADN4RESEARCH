"""
FullTextService - Servicio de aplicación para obtención automática de PDFs.

Orquesta la estrategia de tres niveles para obtener textos completos:
1. Descarga directa desde fuente Open Access legítima
2. Búsqueda en fuentes alternativas (repositorios, preprints)
3. Marcado como no disponible (requiere carga manual)
"""

from typing import Protocol, Optional

from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.downloads.domain.value_objects.download_status import DownloadStatus
from apps.acquisition.downloads.domain.value_objects.pdf_source import PdfSource


# ============================================================================
# PORTS (Interfaces para Hexagonal Architecture)
# ============================================================================

class IOpenAccessChecker(Protocol):
    """Port para verificar si un estudio es Open Access."""

    def is_open_access(self, doi) -> bool:
        """
        Verificar si un DOI corresponde a un artículo Open Access.

        Args:
            doi: DOI del estudio (Value Object)

        Returns:
            True si el estudio es Open Access, False en caso contrario
        """
        ...


class IDownloader(Protocol):
    """Port para descargar PDFs desde URLs."""

    def download(self, study: Study) -> Optional[str]:
        """
        Descargar el PDF de un estudio.

        Args:
            study: Estudio a descargar

        Returns:
            Ruta al archivo descargado, o None si falló la descarga
        """
        ...


class IAlternativeSourceFinder(Protocol):
    """Port para buscar PDFs en fuentes alternativas."""

    def find_and_download(self, study: Study) -> Optional[str]:
        """
        Buscar y descargar PDF desde fuentes alternativas.

        Args:
            study: Estudio a buscar

        Returns:
            Ruta al archivo descargado, o None si no se encontró
        """
        ...


class IFileValidator(Protocol):
    """Port para validar archivos PDF."""

    def is_valid_pdf(self, file_path: str) -> bool:
        """
        Verificar si un archivo es un PDF válido.

        Args:
            file_path: Ruta al archivo

        Returns:
            True si es un PDF válido, False en caso contrario
        """
        ...


# ============================================================================
# SERVICIO DE APLICACIÓN
# ============================================================================

class FullTextService:
    """
    Servicio de aplicación para obtención automática de textos completos.

    Responsabilidades:
    1. Verificar si el estudio es Open Access
    2. Descargar desde fuente legítima si es OA
    3. Buscar en fuentes alternativas si no es OA o falla descarga
    4. Validar integridad del archivo descargado
    5. Actualizar estado del estudio
    6. Registrar trazabilidad (origen del PDF)

    Estrategia de tres niveles:
    - Nivel 1: Descarga directa desde fuente OA (Unpaywall, DOAJ)
    - Nivel 2: Búsqueda en repositorios alternativos (CORE, ResearchGate)
    - Nivel 3: Marcado como no disponible → requiere carga manual
    """

    def __init__(
        self,
        oa_checker: IOpenAccessChecker,
        downloader: IDownloader,
        alternative_finder: IAlternativeSourceFinder,
        file_validator: IFileValidator,
    ):
        """
        Inicializar el servicio con sus dependencias.

        Args:
            oa_checker: Checker para verificar Open Access
            downloader: Downloader para descargar PDFs
            alternative_finder: Finder para buscar en fuentes alternativas
            file_validator: Validador de archivos PDF
        """
        self.oa_checker = oa_checker
        self.downloader = downloader
        self.alternative_finder = alternative_finder
        self.file_validator = file_validator

    def obtain_fulltext(self, study: Study) -> Study:
        """
        Obtener el texto completo de un estudio.

        Implementa la estrategia de tres niveles:
        1. Verificar si es OA y descargar desde fuente legítima
        2. Si falla, buscar en fuentes alternativas
        3. Si falla, marcar como no disponible

        Args:
            study: Estudio del que se quiere obtener el texto completo

        Returns:
            Study con pdf_path, pdf_source y download_status actualizados

        Ejemplos:
            # Estudio Open Access
            >>> service = FullTextService(...)
            >>> study_oa = Study.create_discovered(..., doi="10.1000/open.access")
            >>> result = service.obtain_fulltext(study_oa)
            >>> result.download_status
            'texto_completo_disponible'
            >>> result.pdf_source
            'automático'

            # Estudio con paywall (encuentra alternativa)
            >>> study_paywall = Study.create_discovered(..., doi="10.1000/paywall.123")
            >>> result = service.obtain_fulltext(study_paywall)
            >>> result.download_status
            'texto_completo_disponible'
            >>> result.pdf_source
            'alternativo'

            # Estudio que no se encuentra
            >>> study_missing = Study.create_discovered(..., doi="10.1000/missing")
            >>> result = service.obtain_fulltext(study_missing)
            >>> result.download_status
            'no_disponible'
        """
        # 1. Verificar si el estudio es Open Access
        is_oa = False
        if study.doi:
            is_oa = self.oa_checker.is_open_access(study.doi)

        # 2. Intentar descarga directa si es OA
        pdf_path = None
        pdf_source = None

        if is_oa:
            pdf_path = self.downloader.download(study)
            if pdf_path and self.file_validator.is_valid_pdf(pdf_path):
                pdf_source = PdfSource.AUTOMATICO
            else:
                # Reset si el PDF descargado no es válido
                pdf_path = None

        # 3. Si falló descarga directa, buscar en fuentes alternativas
        if not pdf_path:
            pdf_path = self.alternative_finder.find_and_download(study)
            if pdf_path and self.file_validator.is_valid_pdf(pdf_path):
                pdf_source = PdfSource.ALTERNATIVO
            else:
                # Reset si el PDF alternativo no es válido
                pdf_path = None

        # 4. Actualizar el estudio según el resultado
        if pdf_path and pdf_source:
            # Éxito: se obtuvo el PDF válido
            study.pdf_path = pdf_path
            study.pdf_source = pdf_source.value
            study.download_status = DownloadStatus.DISPONIBLE.value
        else:
            # Fallo: no se pudo obtener el PDF o no era válido
            study.download_status = DownloadStatus.NO_DISPONIBLE.value

        return study
