"""
Dependency Injection Container - Composition Root.

Este módulo es el "Composition Root" de la aplicación: el único lugar
donde se ensamblan todas las dependencias.

Responsabilidades:
- Inicializar conectores externos (Scopus, IEEE, Crossref, etc.)
- Inicializar repositorios (DjangoStudyRepository)
- Ensamblar servicios de aplicación con sus dependencias
- Proporcionar interfaces simples para obtener servicios configurados

PRINCIPIO DE INVERSIÓN DE DEPENDENCIAS:
- Los servicios de dominio dependen de INTERFACES (puertos), no de implementaciones
- Este container inyecta las implementaciones CONCRETAS (adaptadores)

Patrón Singleton Simple:
- Los conectores y repositorios se crean una sola vez (lazy initialization)
- Los servicios se pueden crear por solicitud (son livianos)
"""

import os
from typing import Optional

# ============================================================================
# ADAPTERS - Outbound (Infraestructura)
# ============================================================================

# Repositorio
from apps.acquisition.shared.adapters.outbound.repositories.django_study_repository import (
    DjangoStudyRepository
)

# Conectores académicos (cuando se implementen)
# from apps.acquisition.discovery.adapters.outbound.connectors.scopus_connector import ScopusConnector
# from apps.acquisition.discovery.adapters.outbound.connectors.ieee_connector import IeeeConnector
# from apps.acquisition.metadata.adapters.outbound.connectors.crossref_connector import CrossrefConnector

# ============================================================================
# APPLICATION SERVICES
# ============================================================================

# Discovery
# from apps.acquisition.discovery.application.discovery_service import DiscoveryService

# Metadata
# from apps.acquisition.metadata.application.consolidation_service import ConsolidationService

# Downloads
from apps.acquisition.downloads.application.fulltext_service import FullTextService
from apps.acquisition.downloads.application.manual_upload_service import ManualUploadService
from apps.acquisition.downloads.domain.services.file_validator import FileValidator


class Container:
    """
    Dependency Injection Container (Composition Root).

    Patrón: Singleton simple con lazy initialization.
    Todas las dependencias se crean una sola vez y se reutilizan.

    USO:
        # En una vista Django
        service = Container.get_fulltext_service()
        result = service.obtain_fulltext(study)

        # En una tarea Celery
        repo = Container.get_repository()
        studies = repo.find_all_by_status(StudyStatus.DISCOVERED)

    CONFIGURACIÓN:
        Las credenciales se leen de variables de entorno:
        - SCOPUS_API_KEY
        - IEEE_USERNAME, IEEE_PASSWORD
        - CROSSREF_EMAIL (para rate limit más alto)
    """

    # Singleton instances (lazy initialization)
    _repository: Optional[DjangoStudyRepository] = None
    _scopus_connector = None
    _ieee_connector = None
    _crossref_connector = None
    _file_validator = None

    # ========================================================================
    # REPOSITORIO
    # ========================================================================

    @classmethod
    def get_repository(cls) -> DjangoStudyRepository:
        """
        Obtener la instancia del repositorio de estudios.

        Returns:
            DjangoStudyRepository configurado y listo para usar
        """
        if cls._repository is None:
            cls._repository = DjangoStudyRepository()
        return cls._repository

    # ========================================================================
    # SERVICIOS DE DOMINIO
    # ========================================================================

    @classmethod
    def get_file_validator(cls) -> FileValidator:
        """
        Obtener el validador de archivos PDF.

        Returns:
            FileValidator configurado
        """
        if cls._file_validator is None:
            cls._file_validator = FileValidator()
        return cls._file_validator

    # ========================================================================
    # CONECTORES ACADÉMICOS (para Discovery y Metadata)
    # ========================================================================

    # TODO: Descomentar cuando se implementen los conectores reales

    # @classmethod
    # def get_scopus_connector(cls):
    #     """
    #     Obtener conector a Scopus.
    #
    #     Requiere: SCOPUS_API_KEY en variables de entorno
    #     """
    #     if cls._scopus_connector is None:
    #         api_key = os.getenv("SCOPUS_API_KEY")
    #         if not api_key:
    #             raise ValueError("SCOPUS_API_KEY no configurada en variables de entorno")
    #         cls._scopus_connector = ScopusConnector(api_key=api_key)
    #     return cls._scopus_connector

    # @classmethod
    # def get_ieee_connector(cls):
    #     """
    #     Obtener conector a IEEE Xplore.
    #
    #     Requiere: IEEE_USERNAME, IEEE_PASSWORD en variables de entorno
    #     """
    #     if cls._ieee_connector is None:
    #         username = os.getenv("IEEE_USERNAME")
    #         password = os.getenv("IEEE_PASSWORD")
    #         if not username or not password:
    #             raise ValueError("IEEE_USERNAME y IEEE_PASSWORD deben estar configurados")
    #         cls._ieee_connector = IeeeConnector(username=username, password=password)
    #     return cls._ieee_connector

    # @classmethod
    # def get_crossref_connector(cls):
    #     """
    #     Obtener conector a Crossref.
    #
    #     Requiere (opcional): CROSSREF_EMAIL para rate limit más alto
    #     """
    #     if cls._crossref_connector is None:
    #         email = os.getenv("CROSSREF_EMAIL", None)
    #         cls._crossref_connector = CrossrefConnector(email=email)
    #     return cls._crossref_connector

    # ========================================================================
    # APPLICATION SERVICES (ensamblados con dependencias)
    # ========================================================================

    # @classmethod
    # def get_discovery_service(cls) -> DiscoveryService:
    #     """
    #     Obtener servicio de descubrimiento de estudios (Feature 2).
    #
    #     Returns:
    #         DiscoveryService con conectores y repositorio inyectados
    #     """
    #     connectors = {
    #         "Scopus": cls.get_scopus_connector(),
    #         "IEEE Xplore": cls.get_ieee_connector(),
    #     }
    #
    #     return DiscoveryService(
    #         connectors=connectors,
    #         repository=cls.get_repository(),
    #     )

    # @classmethod
    # def get_consolidation_service(cls) -> ConsolidationService:
    #     """
    #     Obtener servicio de consolidación de metadatos (Feature 3).
    #
    #     Returns:
    #         ConsolidationService con conectores inyectados
    #     """
    #     connectors = {
    #         "Scopus": cls.get_scopus_connector(),
    #         "IEEE Xplore": cls.get_ieee_connector(),
    #         "Crossref": cls.get_crossref_connector(),
    #     }
    #
    #     return ConsolidationService(connectors=connectors)

    @classmethod
    def get_fulltext_service_with_mocks(cls) -> FullTextService:
        """
        Obtener servicio de descarga de textos completos CON MOCKS (Feature 4).

        NOTA: Esta versión usa mocks para BDD/testing.
        Para producción, usar get_fulltext_service() con conectores reales.

        Returns:
            FullTextService con mocks inyectados
        """
        from apps.acquisition.shared.testing.mocks.downloads import (
            build_fulltext_service_with_mocks
        )
        return build_fulltext_service_with_mocks()

    @classmethod
    def get_manual_upload_service(cls) -> ManualUploadService:
        """
        Obtener servicio de carga manual de PDFs (Feature 4).

        Returns:
            ManualUploadService con FileValidator inyectado
        """
        return ManualUploadService(
            file_validator=cls.get_file_validator()
        )

    # TODO: Cuando se implementen los conectores reales de downloads
    # @classmethod
    # def get_fulltext_service(cls) -> FullTextService:
    #     """
    #     Obtener servicio de descarga de textos completos (Feature 4 - PRODUCCIÓN).
    #
    #     Returns:
    #         FullTextService con conectores reales inyectados
    #     """
    #     from apps.acquisition.downloads.adapters.outbound.connectors.unpaywall_connector import UnpaywallConnector
    #     from apps.acquisition.downloads.adapters.outbound.connectors.http_downloader import HttpDownloader
    #     from apps.acquisition.downloads.adapters.outbound.connectors.alternative_finder import AlternativeSourceFinder
    #
    #     return FullTextService(
    #         oa_checker=UnpaywallConnector(email=os.getenv("CROSSREF_EMAIL")),
    #         downloader=HttpDownloader(),
    #         alternative_finder=AlternativeSourceFinder(),
    #         file_validator=cls.get_file_validator(),
    #     )

    # ========================================================================
    # UTILIDADES
    # ========================================================================

    @classmethod
    def reset(cls):
        """
        Resetear todas las instancias singleton.

        Útil para testing cuando necesitas "limpiar" el container.
        """
        cls._repository = None
        cls._scopus_connector = None
        cls._ieee_connector = None
        cls._crossref_connector = None
        cls._file_validator = None
