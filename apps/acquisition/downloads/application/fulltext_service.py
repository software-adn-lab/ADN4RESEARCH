"""
FullTextService - Servicio de aplicación para obtención automática de PDFs.

Orquesta la estrategia de tres niveles para obtener textos completos:
1. Descarga directa desde fuente Open Access legítima
2. Búsqueda en fuentes alternativas (repositorios, preprints)
3. Marcado como no disponible (requiere carga manual)
"""

import logging
from typing import Protocol, Optional, List, Dict, Any

from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.shared.domain.repositories.i_study_repository import IStudyRepository
from apps.acquisition.downloads.domain.value_objects.download_status import DownloadStatus
from apps.acquisition.downloads.domain.value_objects.pdf_source import PdfSource

logger = logging.getLogger(__name__)


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
        repository: Optional[IStudyRepository] = None,
    ):
        """
        Inicializar el servicio con sus dependencias.

        Args:
            oa_checker: Checker para verificar Open Access
            downloader: Downloader para descargar PDFs
            alternative_finder: Finder para buscar en fuentes alternativas
            file_validator: Validador de archivos PDF
            repository: Repositorio de estudios (opcional, para métodos con persistencia)
        """
        self.oa_checker = oa_checker
        self.downloader = downloader
        self.alternative_finder = alternative_finder
        self.file_validator = file_validator
        self.repository = repository

    def download_fulltext(self, study_id: str) -> Study:
        """
        Descargar texto completo de un estudio (CON PERSISTENCIA).

        Args:
            study_id: ID del estudio

        Returns:
            Study con pdf_path y download_status actualizados y persistido

        Raises:
            ValueError: Si el estudio no existe

        Ejemplo:
            >>> service = Container.get_fulltext_service_production()
            >>> study = service.download_fulltext("uuid-1")
            >>> study.download_status
            'texto_completo_disponible'
        """
        # 1. Recuperar estudio
        study = self._get_study_or_raise(study_id)

        # 2. Intentar descarga (lógica pura)
        logger.info(f"Intentando descarga automática para estudio {study_id}...")
        self._obtain_fulltext_in_place(study)

        # 3. Persistir cambios
        saved_study = self.repository.save(study)

        logger.info(
            f"Descarga completada para {study_id}: "
            f"status={saved_study.download_status}, "
            f"source={saved_study.pdf_source}"
        )

        return saved_study

    def download_batch(self, study_ids: List[str]) -> Dict[str, Any]:
        """
        Descargar textos completos de múltiples estudios (CON PERSISTENCIA).

        Args:
            study_ids: Lista de IDs de estudios

        Returns:
            Dict con estadísticas del proceso:
            {
                "total": int,
                "downloaded": int,
                "already_available": int,
                "not_available": int,
                "errors": int
            }

        Ejemplo:
            >>> service = Container.get_fulltext_service_production()
            >>> result = service.download_batch(["uuid-1", "uuid-2"])
            >>> result["downloaded"]
            2
        """
        if not study_ids:
            logger.warning("download_batch llamado con lista vacía")
            return self._create_empty_stats()

        stats = {
            "total": len(study_ids),
            "downloaded": 0,
            "already_available": 0,
            "not_available": 0,
            "errors": 0,
        }

        studies_to_save = []

        for study_id in study_ids:
            try:
                # 1. Recuperar estudio
                study = self.repository.find_by_id(study_id)
                if study is None:
                    logger.warning(f"Estudio no encontrado: {study_id}")
                    stats["errors"] += 1
                    continue

                # 2. Verificar si ya tiene PDF
                if study.pdf_path:
                    logger.info(f"Estudio {study_id} ya tiene PDF: {study.pdf_path}")
                    stats["already_available"] += 1
                    continue

                # 3. Intentar descarga (lógica pura)
                self._obtain_fulltext_in_place(study)

                # 4. Acumular para batch save
                studies_to_save.append(study)

                # 5. Actualizar estadísticas
                if study.pdf_path:
                    stats["downloaded"] += 1
                else:
                    stats["not_available"] += 1

            except Exception as e:
                logger.error(f"Error descargando estudio {study_id}: {e}", exc_info=True)
                stats["errors"] += 1

        # 6. Persistir todos los cambios en batch
        if studies_to_save:
            logger.info(f"Persistiendo {len(studies_to_save)} estudios actualizados...")
            self.repository.save_batch(studies_to_save)

        logger.info(
            f"Descarga batch completada: {stats['downloaded']} descargados, "
            f"{stats['already_available']} ya disponibles, "
            f"{stats['not_available']} no disponibles, "
            f"{stats['errors']} errores"
        )

        return stats

    def get_download_status(self, study_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Obtener estado de descarga de múltiples estudios.

        Args:
            study_ids: Lista de IDs de estudios

        Returns:
            Lista de dicts con info de descarga por estudio

        Ejemplo:
            >>> service = Container.get_fulltext_service_production()
            >>> statuses = service.get_download_status(["uuid-1", "uuid-2"])
            >>> statuses[0]["download_status"]
            'texto_completo_disponible'
        """
        results = []
        for study_id in study_ids:
            study = self.repository.find_by_id(study_id)
            if study:
                results.append({
                    "study_id": study.id,
                    "title": study.title,
                    "download_status": study.download_status,
                    "pdf_path": study.pdf_path,
                    "pdf_source": study.pdf_source,
                })
            else:
                logger.warning(f"Estudio no encontrado: {study_id}")

        return results

    # ==========================================================================
    # HELPERS PRIVADOS (lógica pura en memoria)
    # ==========================================================================

    def _get_study_or_raise(self, study_id: str) -> Study:
        """Recupera estudio o lanza excepción."""
        study = self.repository.find_by_id(study_id)
        if study is None:
            raise ValueError(f"Estudio no encontrado: {study_id}")
        return study

    def _obtain_fulltext_in_place(self, study: Study) -> None:
        """
        Obtener el texto completo de un estudio (en memoria, sin persistir).

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
        # 1. Verificar si el estudio es Open Access (usar hint de discovery si existe)
        is_oa = False
        if study.is_open_access is True:
            is_oa = True
        elif study.doi:
            try:
                # Algunos checkers aceptan (doi, study) para enriquecer pdf_url/is_open_access
                is_oa = self.oa_checker.is_open_access(study.doi, study)  # type: ignore[arg-type]
            except TypeError:
                is_oa = self.oa_checker.is_open_access(study.doi)

        # Guardar el resultado para futuras fases si no se tenía
        if study.is_open_access is None or (study.is_open_access is False and is_oa):
            study.is_open_access = is_oa

        pdf_path = None
        pdf_source = None

        # 2. Intentar descarga directa SOLO si tenemos URL confiable del discovery
        # (IEEE/Scopus suelen proveer pdf_url directa cuando es OA)
        if study.pdf_url:
            pdf_path = self.downloader.download_from_url(study.pdf_url, study.id)
            if pdf_path and self.file_validator.is_valid_pdf(pdf_path):
                pdf_source = PdfSource.AUTOMATICO
            else:
                # Reset si el PDF descargado no es válido
                pdf_path = None

        # 3. Si no tenemos PDF directo, intentar obtener URL OA enriquecida (Unpaywall)
        if not pdf_path and study.doi:
            oa_info_getter = getattr(self.oa_checker, "get_oa_info", None)
            if callable(oa_info_getter):
                oa_info = oa_info_getter(study.doi)
            else:
                oa_info = None

            if isinstance(oa_info, dict):
                # Actualizar hint de OA si se descubre ahora
                if study.is_open_access is None and oa_info.get("is_oa") is not None:
                    study.is_open_access = bool(oa_info.get("is_oa"))

                candidate_url = oa_info.get("pdf_url") or oa_info.get("landing_url")
                if candidate_url:
                    pdf_path = self.downloader.download_from_url(candidate_url, study.id)
                    if pdf_path and self.file_validator.is_valid_pdf(pdf_path):
                        pdf_source = PdfSource.AUTOMATICO
                    else:
                        pdf_path = None

        # 4. Si falló descarga directa, buscar en fuentes alternativas
        if not pdf_path:
            pdf_path = self.alternative_finder.find_and_download(study)
            if pdf_path and self.file_validator.is_valid_pdf(pdf_path):
                pdf_source = PdfSource.ALTERNATIVO
            else:
                # Reset si el PDF alternativo no es válido
                pdf_path = None

        # 5. Actualizar el estudio según el resultado
        if pdf_path and pdf_source:
            # Éxito: se obtuvo el PDF válido
            study.pdf_path = pdf_path
            study.pdf_source = pdf_source.value
            study.download_status = DownloadStatus.DISPONIBLE.value
        else:
            # Fallo: no se pudo obtener el PDF o no era válido
            study.download_status = DownloadStatus.NO_DISPONIBLE.value

    def _create_empty_stats(self) -> Dict[str, Any]:
        """Crear estadísticas vacías."""
        return {
            "total": 0,
            "downloaded": 0,
            "already_available": 0,
            "not_available": 0,
            "errors": 0,
        }
