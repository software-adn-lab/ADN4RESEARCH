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
