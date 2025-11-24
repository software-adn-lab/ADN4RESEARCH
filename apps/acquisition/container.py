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
from apps.acquisition.downloads.application.open_access_checker import CompositeOpenAccessChecker
from apps.acquisition.downloads.application.manual_upload_service import ManualUploadService
from apps.acquisition.downloads.domain.services.file_validator import FileValidator

# Downloads - Conectores reales
from apps.acquisition.downloads.adapters.outbound.connectors.unpaywall_checker import UnpaywallChecker
from apps.acquisition.downloads.adapters.outbound.connectors.crossref_open_access_checker import CrossrefOpenAccessChecker
from apps.acquisition.downloads.adapters.outbound.connectors.scopus_institutional_checker import ScopusInstitutionalChecker
from apps.acquisition.downloads.adapters.outbound.connectors.http_downloader import HttpDownloader
from apps.acquisition.downloads.adapters.outbound.connectors.alternative_source_finder import AlternativeSourceFinder


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

    # Downloads - Production connectors
    _unpaywall_checker = None
    _crossref_checker = None
    _scopus_oa_checker = None
    _http_downloader = None
    _alternative_finder = None
    _fulltext_service_production = None

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

    @classmethod
    def get_fulltext_service_production(cls) -> FullTextService:
        """
        Obtener servicio de descarga de textos completos (Feature 4 - PRODUCCIÓN).

        Usa conectores REALES:
        - UnpaywallChecker para verificar Open Access
        - HttpDownloader para descargar PDFs
        - AlternativeSourceFinder (stub por ahora)
        - FileValidator para validar PDFs

        CONFIGURACIÓN REQUERIDA (.env):
        - UNPAYWALL_EMAIL: Email para API de Unpaywall (reutilizado para Crossref User-Agent)
          (si no está, se intenta usar EPN_USER / IEEE_USERNAME como fallback)
        - PAPERS_STORAGE_DIR: Directorio donde guardar PDFs (opcional, default: media/papers)

        Returns:
            FullTextService con conectores reales inyectados

        Uso:
            service = Container.get_fulltext_service_production()
            result = service.obtain_fulltext(study)
        """
        if cls._fulltext_service_production is None:
            # Leer configuración de entorno
            email = (
                os.getenv("UNPAYWALL_EMAIL")
                or os.getenv("EPN_USER")
                or os.getenv("IEEE_USERNAME")
            )
            if not email:
                raise ValueError(
                    "UNPAYWALL_EMAIL no configurado en .env. "
                    "Proporciona UNPAYWALL_EMAIL o reutiliza EPN_USER/IEEE_USERNAME."
                )

            storage_dir = os.getenv("PAPERS_STORAGE_DIR", "media/papers")
            scopus_api_key = os.getenv("SCOPUS_API_KEY")

            # Crear conectores
            if cls._unpaywall_checker is None:
                cls._unpaywall_checker = UnpaywallChecker(email=email)

            if cls._crossref_checker is None:
                cls._crossref_checker = CrossrefOpenAccessChecker(email=email)

            if cls._scopus_oa_checker is None and scopus_api_key:
                cls._scopus_oa_checker = ScopusInstitutionalChecker(api_key=scopus_api_key)

            if cls._http_downloader is None:
                cls._http_downloader = HttpDownloader(base_dir=storage_dir)

            if cls._alternative_finder is None:
                cls._alternative_finder = AlternativeSourceFinder()

            # Ensamblar servicio con checker compuesto (Unpaywall primario, Crossref secundario)
            oa_checker = CompositeOpenAccessChecker(
                primary_checker=cls._unpaywall_checker,
                secondary_checker=cls._crossref_checker,
                tertiary_checker=cls._scopus_oa_checker
            )

            cls._fulltext_service_production = FullTextService(
                oa_checker=oa_checker,
                downloader=cls._http_downloader,
                alternative_finder=cls._alternative_finder,
                file_validator=cls.get_file_validator(),
            )

        return cls._fulltext_service_production

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
        cls._unpaywall_checker = None
        cls._http_downloader = None
        cls._alternative_finder = None
        cls._fulltext_service_production = None
