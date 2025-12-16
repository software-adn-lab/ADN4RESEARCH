"""
HttpDownloader - Implementación REAL de IDownloader para descargar PDFs vía HTTP.

Este adaptador descarga PDFs desde URLs y los guarda en el sistema de archivos.
"""

import os
import requests
import logging
from pathlib import Path
from typing import Optional, Any

from apps.acquisition.shared.domain.entities.study import Study

logger = logging.getLogger(__name__)


class HttpDownloader:
    """
    Implementación REAL del contrato IDownloader.

    Descarga PDFs desde URLs HTTP/HTTPS y los guarda usando el IStorage configurado via Adapter.
    
    Asegura consistencia entre lo que se descarga y lo que se persiste en MinIO/S3/Local.
    """

    def __init__(self, storage: Any, timeout: float = 30.0):
        """
        Inicializar el descargador HTTP.

        Args:
            storage: Implementación de IStorage (DjangoStorage)
            timeout: Timeout en segundos para descargas
        """
        self.storage = storage
        self.timeout = timeout
        logger.info(f"HttpDownloader inicializado con storage: {type(storage).__name__}")

    def download(self, study: Study) -> Optional[str]:
        """
        Descarga el PDF de un estudio desde su URL y lo guarda en el storage.
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

        # Construir path relativo para el storage
        # Estructura: <uuid>/automatic/<uuid>.pdf
        filename = f"{study.id}.pdf"
        relative_path = f"{study.id}/automatic/{filename}"

        # Si ya existe en el storage, no descargar de nuevo
        if self.storage.exists(relative_path):
            logger.info(f"PDF ya existe en storage: {relative_path}")
            return relative_path

        logger.info(f"Descargando PDF para {study.doi.value}...")

        return self._download_and_save(doi_url, relative_path)

    def download_from_url(self, url: str, study_id: str) -> Optional[str]:
        """
        Método auxiliar para descargar desde una URL específica (Unpaywall direct link).
        """
        filename = f"{study_id}.pdf"
        relative_path = f"{study_id}/automatic/{filename}"

        if self.storage.exists(relative_path):
            logger.info(f"PDF ya existe en storage: {relative_path}")
            return relative_path

        logger.info(f"Descargando desde URL directa: {url}")
        return self._download_and_save(url, relative_path)

    def _download_and_save(self, url: str, relative_path: str) -> Optional[str]:
        """Helper para descargar y guardar."""
        try:
            response = requests.get(url, stream=True, timeout=self.timeout, allow_redirects=True)

            if response.status_code != 200:
                logger.warning(f"HTTP {response.status_code} para {url}")
                return None

            # Verificar Content-Type
            content_type = response.headers.get('Content-Type', '').lower()
            if content_type and 'pdf' not in content_type and 'octet-stream' not in content_type:
                logger.warning(f"Content-Type no es PDF: {content_type} para {url}")

            # Leer contenido en memoria (cuidado con archivos muy grandes, pero papers suelen ser <10MB)
            content = response.content

            # Validar magic bytes antes de guardar
            if not content.startswith(b'%PDF'):
                logger.error(f"Contenido descargado no es un PDF válido (magic bytes query).")
                return None

            # Guardar en Storage
            from django.core.files.base import ContentFile
            saved_path = self.storage.save(relative_path, ContentFile(content))

            # VERIFICACIÓN ESTRICTA: Asegurar que el archivo realmente existe en el storage
            if not self.storage.exists(saved_path):
                logger.error(f"CRÍTICO: Storage reportó éxito pero el archivo no existe: {saved_path}")
                return None

            logger.info(f"✅ PDF guardado y verificado en storage: {saved_path}")
            return saved_path

        except requests.Timeout:
            logger.error(f"Timeout descargando {url}")
            return None
        except requests.RequestException as e:
            logger.error(f"Error de red descargando {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado guardando en storage: {e}")
            return None
