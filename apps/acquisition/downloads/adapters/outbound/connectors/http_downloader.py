"""
HttpDownloader - Implementación REAL de IDownloader para descargar PDFs vía HTTP.

Este adaptador descarga PDFs desde URLs y los guarda en el sistema de archivos.
"""

import os
import requests
import logging
from pathlib import Path
from typing import Optional

from apps.acquisition.shared.domain.entities.study import Study

logger = logging.getLogger(__name__)


class HttpDownloader:
    """
    Implementación REAL del contrato IDownloader.

    Descarga PDFs desde URLs HTTP/HTTPS y los guarda en disco.

    Uso:
        downloader = HttpDownloader(base_dir="media/papers")
        pdf_path = downloader.download(study)
    """

    def __init__(self, base_dir: str, timeout: float = 30.0):
        """
        Inicializar el descargador HTTP.

        Args:
            base_dir: Directorio base donde guardar los PDFs
            timeout: Timeout en segundos para descargas
        """
        self.base_dir = Path(base_dir)
        self.timeout = timeout

        # Crear directorio si no existe
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"HttpDownloader inicializado: {self.base_dir}")

    def download(self, study: Study) -> Optional[str]:
        """
        Implementación del contrato IDownloader.

        Descarga el PDF de un estudio desde su URL y lo guarda.

        ESTRATEGIA ACTUAL:
        - Usa el DOI URL como fuente de descarga
        - Futuro: podría recibir la URL desde Unpaywall directamente

        Args:
            study: Estudio del que descargar el PDF

        Returns:
            Ruta absoluta al archivo descargado o None si falla

        Ejemplos:
            >>> downloader = HttpDownloader("media/papers")
            >>> study = Study.create_discovered(...)
            >>> path = downloader.download(study)
            >>> path
            '/path/to/media/papers/abc-123-def.pdf'
        """
        # Validación básica
        if not study.doi:
            logger.warning(f"Study {study.id} no tiene DOI, no se puede descargar")
            return None

        # Obtener URL del DOI
        doi_url = study.get_doi_url()
        if not doi_url:
            logger.warning(f"No se pudo construir URL para DOI: {study.doi.value}")
            return None

        # Construir path de destino
        filename = f"{study.id}.pdf"
        file_path = self.base_dir / filename

        # Si ya existe, no descargar de nuevo
        if file_path.exists():
            logger.info(f"PDF ya existe: {file_path}")
            return str(file_path)

        logger.info(f"Descargando PDF para {study.doi.value}...")

        try:
            # Descarga con streaming para no consumir toda la memoria
            response = requests.get(doi_url, stream=True, timeout=self.timeout, allow_redirects=True)

            # Verificar status
            if response.status_code != 200:
                logger.warning(f"HTTP {response.status_code} para {doi_url}")
                return None

            # Verificar Content-Type (flexible, algunos servers no lo setean bien)
            content_type = response.headers.get('Content-Type', '').lower()
            if content_type and 'pdf' not in content_type and 'octet-stream' not in content_type:
                logger.warning(f"Content-Type no es PDF: {content_type} para {doi_url}")
                # No retornamos None todavía, algunos servers no setean bien el header

            # Guardar archivo
            total_size = 0
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)

            logger.info(f"✅ PDF descargado: {filename} ({total_size / 1024:.2f} KB)")

            # Validación básica: verificar magic bytes PDF
            if not self._is_valid_pdf_magic_bytes(file_path):
                logger.error(f"Archivo descargado no es un PDF válido: {file_path}")
                # Eliminar archivo inválido
                file_path.unlink()
                return None

            return str(file_path)

        except requests.Timeout:
            logger.error(f"Timeout descargando {doi_url}")
            return None

        except requests.RequestException as e:
            logger.error(f"Error de red descargando {doi_url}: {e}")
            return None

        except Exception as e:
            logger.error(f"Error inesperado descargando {doi_url}: {e}")
            # Limpiar archivo parcial si existe
            if file_path.exists():
                file_path.unlink()
            return None

    def download_from_url(self, url: str, study_id: str) -> Optional[str]:
        """
        Método auxiliar para descargar desde una URL específica (no parte del contrato).

        Útil cuando Unpaywall nos da una URL directa al PDF.

        Args:
            url: URL directa al PDF
            study_id: ID del estudio (para nombrar el archivo)

        Returns:
            Ruta al archivo descargado o None
        """
        filename = f"{study_id}.pdf"
        file_path = self.base_dir / filename

        if file_path.exists():
            logger.info(f"PDF ya existe: {file_path}")
            return str(file_path)

        logger.info(f"Descargando desde URL directa: {url}")

        try:
            response = requests.get(url, stream=True, timeout=self.timeout, allow_redirects=True)

            if response.status_code != 200:
                logger.warning(f"HTTP {response.status_code} para {url}")
                return None

            total_size = 0
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)

            logger.info(f"✅ PDF descargado: {filename} ({total_size / 1024:.2f} KB)")

            if not self._is_valid_pdf_magic_bytes(file_path):
                logger.error(f"Archivo descargado no es un PDF válido: {file_path}")
                file_path.unlink()
                return None

            return str(file_path)

        except Exception as e:
            logger.error(f"Error descargando desde {url}: {e}")
            if file_path.exists():
                file_path.unlink()
            return None

    def _is_valid_pdf_magic_bytes(self, file_path: Path) -> bool:
        """
        Verificar que un archivo tenga los magic bytes de PDF (%PDF).

        Args:
            file_path: Ruta al archivo a verificar

        Returns:
            True si tiene magic bytes válidos
        """
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
                return header == b'%PDF'
        except Exception:
            return False
