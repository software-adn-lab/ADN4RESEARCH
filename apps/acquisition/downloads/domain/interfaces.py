"""
Domain interfaces (Ports) for downloads module.

Estos Protocols definen los contratos que deben cumplir los adaptadores externos.
Permiten desacoplar la lógica de aplicación de las implementaciones concretas.

Patrones implementados:
- Chain of Responsibility: BaseOpenAccessChecker permite encadenar checkers
- Protocol: IOpenAccessChecker define el contrato estructural
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, Optional, Dict, Any

from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.shared.domain.value_objects.doi import DOI


# ============================================================================ #
# Value Object para resultado de verificación OA
# ============================================================================ #


@dataclass
class OpenAccessResult:
    """
    Resultado de verificación de Open Access.
    
    Value Object que encapsula toda la información de una consulta OA.
    Usar este objeto en lugar de diccionarios para type-safety.
    """
    is_oa: bool
    pdf_url: Optional[str] = None
    landing_url: Optional[str] = None
    source: Optional[str] = None
    oa_type: Optional[str] = None
    license: Optional[str] = None
    version: Optional[str] = None
    
    @classmethod
    def not_found(cls, source: str = "Unknown") -> "OpenAccessResult":
        """Factory method para resultado negativo."""
        return cls(is_oa=False, source=source)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OpenAccessResult":
        """Factory method para crear desde diccionario."""
        return cls(
            is_oa=bool(data.get("is_oa", False)),
            pdf_url=data.get("pdf_url"),
            landing_url=data.get("landing_url"),
            source=data.get("source"),
            oa_type=data.get("oa_type"),
            license=data.get("license"),
            version=data.get("version"),
        )


# ============================================================================ #
# Protocol (Structural Typing)
# ============================================================================ #


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


# ============================================================================ #
# Chain of Responsibility Base Class
# ============================================================================ #


class BaseOpenAccessChecker(ABC):
    """
    Clase base abstracta para checkers de Open Access con Chain of Responsibility.
    
    Implementa el patrón Chain of Responsibility para encadenar múltiples
    fuentes de verificación de OA (Unpaywall -> Crossref -> Scopus).
    
    Cada checker intenta resolver la búsqueda; si no puede, la pasa al siguiente.
    
    Uso típico:
        # Configurar la cadena (en Container o DI)
        scopus = ScopusChecker(api_key="...", next_checker=None)
        crossref = CrossrefChecker(email="...", next_checker=scopus)
        unpaywall = UnpaywallChecker(email="...", next_checker=crossref)
        
        # Inyectar el primero al caso de uso
        result = unpaywall.check_access(doi)
    
    Ventajas:
        - Orden configurable sin modificar código
        - Cada checker tiene una única responsabilidad
        - Fácil agregar/quitar checkers de la cadena
        - Mejor testabilidad (mock del next_checker)
    """
    
    def __init__(self, next_checker: Optional["BaseOpenAccessChecker"] = None):
        """
        Inicializar checker con siguiente eslabón de la cadena.
        
        Args:
            next_checker: Siguiente checker a consultar si este no encuentra OA.
                         None significa que este es el último de la cadena.
        """
        self._next_checker = next_checker
    
    @property
    def source_name(self) -> str:
        """Nombre de la fuente (para logging y resultados)."""
        return self.__class__.__name__.replace("Checker", "").replace("OpenAccess", "")
    
    @abstractmethod
    def check_access(self, doi: DOI) -> OpenAccessResult:
        """
        Verificar Open Access para un DOI.
        
        Implementar en cada subclase con la lógica específica de la fuente.
        Si encuentra OA, retornar OpenAccessResult con is_oa=True.
        Si no encuentra, llamar a self._pass_to_next(doi).
        
        Args:
            doi: DOI a verificar
            
        Returns:
            OpenAccessResult con la información encontrada
        """
        pass
    
    def _pass_to_next(self, doi: DOI) -> OpenAccessResult:
        """
        Pasar la responsabilidad al siguiente eslabón de la cadena.
        
        Llamar este método cuando el checker actual no encuentra OA
        o falla al consultar su fuente.
        
        Args:
            doi: DOI a verificar
            
        Returns:
            OpenAccessResult del siguiente checker, o resultado vacío si no hay más
        """
        if self._next_checker is not None:
            return self._next_checker.check_access(doi)
        return OpenAccessResult.not_found(source="EndOfChain")
    
    def is_open_access(self, doi: DOI, study: Optional[Study] = None) -> bool:
        """
        Implementación del contrato IOpenAccessChecker.
        
        Wrapper que mantiene compatibilidad con la firma del Protocol,
        mientras usa internamente check_access.
        
        Args:
            doi: DOI a verificar
            study: Estudio opcional (ignorado, para compatibilidad)
            
        Returns:
            True si es Open Access, False en caso contrario
        """
        result = self.check_access(doi)
        return result.is_oa
    
    def get_oa_info(self, doi: DOI) -> Dict[str, Any]:
        """
        Obtener información completa de OA como diccionario.
        
        Mantiene compatibilidad con el código existente que espera Dict.
        
        Args:
            doi: DOI a verificar
            
        Returns:
            Diccionario con información OA
        """
        result = self.check_access(doi)
        return {
            "is_oa": result.is_oa,
            "pdf_url": result.pdf_url,
            "landing_url": result.landing_url,
            "source": result.source,
            "oa_type": result.oa_type,
            "license": result.license,
            "version": result.version,
        }


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
