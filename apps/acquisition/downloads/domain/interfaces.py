"""
Domain interfaces (Ports) for downloads module.

Estos Protocols definen los contratos que deben cumplir los adaptadores externos.
Permiten desacoplar la lógica de aplicación de las implementaciones concretas.
"""

from typing import Protocol, Optional

from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.shared.domain.value_objects.doi import DOI


class IOpenAccessChecker(Protocol):
    """Port para verificar si un estudio es Open Access."""

    def is_open_access(self, doi: DOI, study: Optional[Study] = None) -> bool:
        """
        Verificar si un DOI corresponde a un artículo Open Access.

        Args:
            doi: DOI del estudio (Value Object)
            study: Estudio opcional para enriquecimiento

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

    def download_from_url(self, url: str, study_id: str) -> Optional[str]:
        """
        Descargar desde una URL directa.

        Args:
            url: URL del PDF
            study_id: ID del estudio (para nombrar el archivo)

        Returns:
            Ruta al archivo descargado, o None si falló
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


class IStorage(Protocol):
    """
    Port para persistir archivos binarios (PDFs, imágenes, etc.).
    
    Permite cambiar entre diferentes backends de almacenamiento
    (filesystem local, S3/MinIO, Azure Blob, Google Cloud Storage)
    sin modificar la lógica de aplicación.
    """

    def save(self, file_obj, relative_path: str) -> str:
        """
        Guardar un archivo en el storage.

        Args:
            file_obj: Objeto archivo (BinaryIO, UploadedFile)
            relative_path: Ruta relativa dentro del storage

        Returns:
            Ruta donde se guardó el archivo (puede ser URL o path local)
        """
        ...

    def delete(self, path: str) -> None:
        """
        Eliminar un archivo del storage.

        Args:
            path: Ruta al archivo a eliminar
        """
        ...

    def exists(self, path: str) -> bool:
        """
        Verificar si un archivo existe en el storage.

        Args:
            path: Ruta al archivo

        Returns:
            True si existe, False si no
        """
        ...

    def url(self, path: str) -> str:
        """
        Obtener URL pública del archivo.

        Args:
            path: Ruta al archivo

        Returns:
            URL completa (para S3/MinIO) o ruta relativa (para local)
        """
        ...
