"""
IStudyRepository - Interfaz del repositorio para persistir Studies.

Este es un contrato (interfaz) que define cómo persistir y recuperar estudios.
La implementación concreta estará en la capa de infraestructura.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from ..entities.study import Study
from ..value_objects.study_status import StudyStatus


class IStudyRepository(ABC):
    """
    Repositorio para gestionar la persistencia de Studies.

    Este repositorio sigue el patrón Repository de DDD, abstraiendo
    la lógica de persistencia del dominio.

    La implementación concreta puede usar Django ORM, SQLAlchemy,
    o cualquier otro mecanismo de persistencia.
    """

    @abstractmethod
    def save(self, study: Study) -> Study:
        """
        Guardar un estudio (crear o actualizar).

        Args:
            study: El estudio a guardar

        Returns:
            El estudio guardado (con ID si fue creado)

        Raises:
            RepositoryError: Si ocurre un error de persistencia
        """
        pass

    @abstractmethod
    def save_batch(self, studies: List[Study]) -> List[Study]:
        """
        Guardar múltiples estudios en batch (optimizado).

        Args:
            studies: Lista de estudios a guardar

        Returns:
            Lista de estudios guardados

        Raises:
            RepositoryError: Si ocurre un error de persistencia
        """
        pass

    @abstractmethod
    def find_by_id(self, study_id: str) -> Optional[Study]:
        """
        Buscar un estudio por su ID.

        Args:
            study_id: ID del estudio (UUID)

        Returns:
            El estudio si existe, None en caso contrario
        """
        pass

    @abstractmethod
    def find_by_doi(self, doi: str) -> Optional[Study]:
        """
        Buscar un estudio por su DOI.

        Args:
            doi: DOI del estudio

        Returns:
            El estudio si existe, None en caso contrario
        """
        pass

    @abstractmethod
    def find_by_title_and_source(self, title: str, source: str) -> Optional[Study]:
        """
        Buscar un estudio por título y fuente.

        Útil para deduplicación durante el discovery.

        Args:
            title: Título del estudio
            source: Fuente académica

        Returns:
            El estudio si existe, None en caso contrario
        """
        pass

    @abstractmethod
    def find_all_by_status(self, status: StudyStatus) -> List[Study]:
        """
        Obtener todos los estudios con un estado específico.

        Args:
            status: Estado a filtrar

        Returns:
            Lista de estudios con ese estado
        """
        pass

    @abstractmethod
    def find_all(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Study]:
        """
        Obtener todos los estudios con paginación opcional.

        Args:
            limit: Número máximo de resultados (None = sin límite)
            offset: Número de resultados a saltar (None = desde el inicio)

        Returns:
            Lista de estudios
        """
        pass

    @abstractmethod
    def count_by_status(self, status: StudyStatus) -> int:
        """
        Contar estudios por estado.

        Args:
            status: Estado a contar

        Returns:
            Número de estudios con ese estado
        """
        pass

    @abstractmethod
    def delete(self, study_id: str) -> bool:
        """
        Eliminar un estudio por su ID.

        Args:
            study_id: ID del estudio a eliminar

        Returns:
            True si se eliminó, False si no existía
        """
        pass

    @abstractmethod
    def exists_by_doi(self, doi: str) -> bool:
        """
        Verificar si existe un estudio con un DOI específico.

        Args:
            doi: DOI a verificar

        Returns:
            True si existe, False en caso contrario
        """
        pass

    @abstractmethod
    def exists_by_title_and_source(self, title: str, source: str) -> bool:
        """
        Verificar si existe un estudio con título y fuente específicos.

        Útil para deduplicación rápida.

        Args:
            title: Título del estudio
            source: Fuente académica

        Returns:
            True si existe, False en caso contrario
        """
        pass
