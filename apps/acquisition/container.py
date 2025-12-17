"""
Dependency Injection Container - Composition Root.

Este módulo es el "composition root" de Acquisition:
el único lugar donde se ensamblan todas las dependencias concretas.

Responsabilidades:
- Inicializar conectores externos (Scopus, IEEE, Crossref, etc.)
- Inicializar repositorios (DjangoStudyRepository)
- Ensamblar servicios de aplicación con sus dependencias
- Exponer métodos de clase para obtener servicios ya configurados

Principio de inversión de dependencias:
- Los servicios de dominio dependen de interfaces/puertos
- Este container inyecta implementaciones concretas (adaptadores)

Patrón Singleton simple:
- Conectores y repositorios se crean una sola vez (lazy initialization)
- Los servicios se crean una vez y se reutilizan (son livianos)
"""

import os
from typing import Optional, Dict, Any

from apps.acquisition.shared.adapters.outbound.repositories.django_study_repository import (
    DjangoStudyRepository,
)

# Application services
from apps.acquisition.translation.application.translation_service import TranslationService
from apps.acquisition.discovery.application.discovery_service import DiscoveryService
from apps.acquisition.shared.application.acquisition_orchestrator import AcquisitionOrchestrator

from apps.acquisition.downloads.application.fulltext_service import FullTextService
from apps.acquisition.downloads.application.open_access_checker import ChainedOpenAccessChecker
from apps.acquisition.downloads.application.manual_upload_service import ManualUploadService
from apps.acquisition.downloads.application.manual_upload_app_service import (
    ManualUploadAppService,
)
from apps.acquisition.downloads.domain.services.file_validator import FileValidator
from apps.acquisition.downloads.domain.interfaces import BaseOpenAccessChecker

from apps.acquisition.downloads.adapters.outbound.connectors import (
    UnpaywallChecker,
    CrossrefOpenAccessChecker,
    ScopusInstitutionalChecker,
    HttpDownloader,
    SciHubDownloader,
    AlternativeSourceFinder,
)
from apps.acquisition.downloads.adapters.outbound.storage.local_file_storage import (
    LocalFileStorage,
)
from apps.acquisition.downloads.adapters.outbound.storage.django_storage import (
    DjangoStorage,
)

from apps.acquisition.discovery.application.manual_study_service import ManualStudyService
from apps.acquisition.metadata.application.manual_edit_service import ManualEditService
from apps.acquisition.metadata.application.consolidation_service import ConsolidationService


class Container:
    """
    Dependency Injection Container (Composition Root).

    Uso típico:

        # En una vista Django
        service = Container.get_fulltext_service_production()
        result = service.obtain_fulltext(study)

        # En una tarea Celery
        repo = Container.get_repository()
        studies = repo.find_all_by_status(StudyStatus.DISCOVERED)

    Las credenciales se leen de variables de entorno, por ejemplo:
    - SCOPUS_API_KEY
    - IEEE_USERNAME / IEEE_PASSWORD (o EPN_USER / EPN_PASS)
    - UNPAYWALL_EMAIL
    """

    # --------------------------------------------------------------------- #
    # Singletons (lazy initialization)
    # --------------------------------------------------------------------- #

    # Repositorio
    _repository: Optional[DjangoStudyRepository] = None

    # Conectores (reservados para uso futuro si se centralizan aquí)
    _scopus_connector = None
    _ieee_connector = None
    _crossref_connector = None

    # Servicios de dominio / aplicación
    _file_validator: Optional[FileValidator] = None
    _translation_service: Optional[TranslationService] = None
    _discovery_service: Optional[DiscoveryService] = None
    _preview_discovery_service: Optional[DiscoveryService] = None
    _orchestrator: Optional[AcquisitionOrchestrator] = None

    # Application services (con persistencia)
    _manual_study_service: Optional[ManualStudyService] = None
    _manual_edit_service: Optional[ManualEditService] = None
    _consolidation_service: Optional[ConsolidationService] = None

    # Descargas (Feature 4) - Chain of Responsibility
    _oa_checker_chain: Optional[BaseOpenAccessChecker] = None  # Cabeza de la cadena
    _http_downloader: Optional[HttpDownloader] = None
    _alternative_finder: Optional[AlternativeSourceFinder] = None
    _fulltext_service_production: Optional[FullTextService] = None
    _storage: Optional[DjangoStorage] = None
    _manual_upload_app_service: Optional[ManualUploadAppService] = None

    # --------------------------------------------------------------------- #
    # Helpers privados
    # --------------------------------------------------------------------- #

    @classmethod
    def _build_discovery_connectors(cls) -> Dict[str, Any]:
        """
        Construye los conectores reales usados por Discovery (Scopus, IEEE).

        Usa la nueva arquitectura con estrategias (API + Web).
        Se usa tanto para el servicio productivo como para el de preview.
        """
        # Imports de la nueva estructura
        from apps.acquisition.discovery.adapters.outbound.connectors import (
            ScopusConnector,
            IeeeConnector,
        )
        from apps.acquisition.discovery.adapters.outbound.connectors.scopus.strategies.api_strategy import (
            ScopusApiStrategy,
        )
        from apps.acquisition.discovery.adapters.outbound.connectors.scopus.strategies.web_strategy import (
            ScopusWebStrategy,
        )
        from apps.acquisition.discovery.adapters.outbound.connectors.ieee.strategies.api_strategy import (
            IeeeApiStrategy,
        )
        from apps.acquisition.discovery.adapters.outbound.connectors.ieee.strategies.web_strategy import (
            IeeeWebStrategy,
        )
        from apps.acquisition.discovery.infrastructure.http.http_client import HttpClient
        from apps.acquisition.discovery.infrastructure.http.rate_limiter import RateLimiter
        from apps.acquisition.discovery.infrastructure.normalization.ieee_result_normalizer import (
            IeeeResultNormalizer,
        )
        from apps.acquisition.discovery.infrastructure.normalization.scopus_result_normalizer import (
            ScopusResultNormalizer,
        )
        from apps.acquisition.discovery.infrastructure.config.connector_config import (
            IeeeConfig,
            ScopusConfig,
        )
        from apps.acquisition.shared.infrastructure.circuit_breaker import CircuitBreaker

        # Configuración y credenciales
        scopus_api_key = os.getenv("SCOPUS_API_KEY")
        epn_user = os.getenv("EPN_USER")
        epn_pass = os.getenv("EPN_PASS")
        ieee_user = os.getenv("IEEE_USERNAME") or epn_user
        ieee_pass = os.getenv("IEEE_PASSWORD") or epn_pass

        # Infraestructura compartida
        http_client = HttpClient()

        # --- ENSAMBLAJE DE SCOPUS ---
        scopus_config = ScopusConfig()
        scopus_normalizer = ScopusResultNormalizer()
        scopus_rate_limiter = RateLimiter(rate=scopus_config.rate_limit)

        # Estrategias Scopus
        scopus_api_strategy = None
        if scopus_api_key:
            scopus_api_strategy = ScopusApiStrategy(
                http_client=http_client,
                normalizer=scopus_normalizer,
                api_key=scopus_api_key,
            )

        scopus_web_strategy = ScopusWebStrategy(
            username=epn_user,
            password=epn_pass,
            normalizer=scopus_normalizer,
            headless=True,
        )

        # Conector Scopus (modo nuevo con estrategias inyectadas)
        scopus_connector = ScopusConnector(
            username=epn_user,  # Requerido para fallback
            password=epn_pass,  # Requerido para fallback
            api_key=scopus_api_key,  # Requerido para API
            api_strategy=scopus_api_strategy,
            web_strategy=scopus_web_strategy,
            rate_limiter=scopus_rate_limiter,
            prefer_api=True,
        )

        # --- ENSAMBLAJE DE IEEE ---
        ieee_config = IeeeConfig()
        ieee_normalizer = IeeeResultNormalizer()
        ieee_rate_limiter = RateLimiter(rate=ieee_config.rate_limit)
        ieee_circuit_breaker = CircuitBreaker(
            fail_max=ieee_config.circuit_breaker_threshold,
            timeout_duration=ieee_config.circuit_breaker_timeout,
            name="IEEE",
        )

        # Estrategias IEEE
        ieee_api_strategy = IeeeApiStrategy(
            http_client=http_client,
            normalizer=ieee_normalizer,
        )

        ieee_web_strategy = IeeeWebStrategy(
            username=ieee_user,
            password=ieee_pass,
            normalizer=ieee_normalizer,
            headless=True,
        )

        # Conector IEEE (modo nuevo con estrategias inyectadas)
        ieee_connector = IeeeConnector(
            username=ieee_user,  # Requerido por constructor
            password=ieee_pass,  # Requerido por constructor
            api_strategy=ieee_api_strategy,
            web_strategy=ieee_web_strategy,
            rate_limiter=ieee_rate_limiter,
            circuit_breaker=ieee_circuit_breaker,
            prefer_api=False,
        )

        return {
            "Scopus": scopus_connector,
            "IEEE Xplore": ieee_connector,
        }

    # --------------------------------------------------------------------- #
    # Repositorio
    # --------------------------------------------------------------------- #

    @classmethod
    def get_repository(cls) -> DjangoStudyRepository:
        """
        Repositorio de estudios basado en Django ORM.
        """
        if cls._repository is None:
            cls._repository = DjangoStudyRepository()
        return cls._repository

    # --------------------------------------------------------------------- #
    # Servicios de dominio básicos
    # --------------------------------------------------------------------- #

    @classmethod
    def get_file_validator(cls) -> FileValidator:
        """
        Validador de archivos PDF (estructura básica, tamaño, etc.).
        """
        if cls._file_validator is None:
            cls._file_validator = FileValidator()
        return cls._file_validator

    # --------------------------------------------------------------------- #
    # Translation / Discovery / Orchestrator
    # --------------------------------------------------------------------- #

    @classmethod
    def get_translation_service(cls) -> TranslationService:
        """
        Servicio de traducción de estrategias de búsqueda (Feature 1).
        """
        if cls._translation_service is None:
            cls._translation_service = TranslationService()
        return cls._translation_service

    @classmethod
    def get_discovery_service(cls) -> DiscoveryService:
        """
        Servicio de descubrimiento de estudios (Feature 2 - modo producción).

        - Usa conectores reales (Scopus, IEEE Xplore)
        - Persiste resultados usando el repositorio de estudios
        """
        if cls._discovery_service is None:
            connectors = cls._build_discovery_connectors()
            cls._discovery_service = DiscoveryService(
                connectors=connectors,
                repository=cls.get_repository(),
            )
        return cls._discovery_service

    @classmethod
    def get_preview_discovery_service(cls) -> DiscoveryService:
        """
        Servicio de descubrimiento en modo PREVIEW (sin persistencia).

        - Usa los mismos conectores reales (Scopus, IEEE)
        - Devuelve resultados en memoria
        - NO persiste en base de datos
        - Pensado para Diseño (probar estrategias).
        """
        if cls._preview_discovery_service is None:
            connectors = cls._build_discovery_connectors()
            cls._preview_discovery_service = DiscoveryService(
                connectors=connectors,
                repository=None,  # Sin repositorio = no hay persistencia
            )
        return cls._preview_discovery_service

    @classmethod
    def get_orchestrator(cls) -> AcquisitionOrchestrator:
        """
        Orquestador principal de Acquisition.

        Coordina:
        - Traducción de estrategias
        - Discovery en múltiples proveedores
        - Persistencia y trazabilidad de estudios
        - Gestión manual de estudios y PDFs

        Inyecta TODAS las dependencias (Inversión de Dependencias).
        """
        if cls._orchestrator is None:
            cls._orchestrator = AcquisitionOrchestrator(
                translation_service=cls.get_translation_service(),
                discovery_service=cls.get_discovery_service(),
                study_repository=cls.get_repository(),
                manual_upload_service=cls.get_manual_upload_app_service(),  # INYECCIÓN
            )
        return cls._orchestrator

    # --------------------------------------------------------------------- #
    # Descargas (Full text, manual upload, storage)
    # --------------------------------------------------------------------- #

    @classmethod
    def get_fulltext_service_with_mocks(cls) -> FullTextService:
        """
        Servicio de descarga de full text con mocks (para BDD/testing).

        Para producción usar get_fulltext_service_production().
        """
        from apps.acquisition.shared.testing.mocks.downloads import (
            build_fulltext_service_with_mocks,
        )

        return build_fulltext_service_with_mocks()

    @classmethod
    def get_manual_upload_service(cls) -> ManualUploadService:
        """
        Servicio de dominio para carga manual de PDFs.
        """
        return ManualUploadService(file_validator=cls.get_file_validator())

    @classmethod
    def get_storage(cls) -> DjangoStorage:
        """
        Adaptador de storage que usa Django's default_storage.

        Soporta tanto FileSystemStorage (local) como S3Boto3Storage (MinIO/AWS)
        según la configuración USE_S3 en settings.py.
        """
        if cls._storage is None:
            cls._storage = DjangoStorage()
        return cls._storage

    @classmethod
    def get_manual_upload_app_service(cls) -> ManualUploadAppService:
        """
        Servicio de aplicación para carga manual de PDFs,
        listo para usarse desde vistas/APIs.
        """
        if cls._manual_upload_app_service is None:
            cls._manual_upload_app_service = ManualUploadAppService(
                repository=cls.get_repository(),
                manual_upload_service=cls.get_manual_upload_service(),
                storage=cls.get_storage(),
            )
        return cls._manual_upload_app_service

    @classmethod
    def get_fulltext_service_production(cls) -> FullTextService:
        """
        Servicio de descarga de textos completos (Feature 4 - PRODUCCIÓN).

        Conectores reales (Chain of Responsibility):
        - UnpaywallChecker -> CrossrefOpenAccessChecker -> ScopusInstitutionalChecker
        - HttpDownloader (descarga de PDFs)
        - AlternativeSourceFinder (incluye Sci-Hub opcional)

        Variables de entorno relevantes:
        - UNPAYWALL_EMAIL (recomendado) o EPN_USER / IEEE_USERNAME
        - PAPERS_STORAGE_DIR (destino de PDFs, default: media/papers)
        - SCOPUS_API_KEY (opcional, para ScopusInstitutionalChecker)
        - ENABLE_SCIHUB=true/false (zona gris legal: solo para investigación)
        """
        if cls._fulltext_service_production is None:
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

            # ----------------------------------------------------------------- #
            # Construir Chain of Responsibility para OA Checkers
            # Orden: Unpaywall -> Crossref -> Scopus (si hay API key)
            # ----------------------------------------------------------------- #
            if cls._oa_checker_chain is None:
                # Último eslabón: Scopus (si hay API key)
                scopus_checker = None
                if scopus_api_key:
                    scopus_checker = ScopusInstitutionalChecker(
                        api_key=scopus_api_key,
                        next_checker=None,  # Fin de la cadena
                    )

                # Eslabón medio: Crossref -> Scopus
                crossref_checker = CrossrefOpenAccessChecker(
                    email=email,
                    next_checker=scopus_checker,
                )

                # Primer eslabón: Unpaywall -> Crossref
                cls._oa_checker_chain = UnpaywallChecker(
                    email=email,
                    next_checker=crossref_checker,
                )

            # Descarga y fuentes alternativas
            if cls._http_downloader is None:
                cls._http_downloader = HttpDownloader(storage=cls.get_storage())

            if cls._alternative_finder is None:
                enable_scihub = os.getenv("ENABLE_SCIHUB", "false").lower() == "true"

                scihub = SciHubDownloader(
                    storage=cls.get_storage(),
                    enabled=enable_scihub,
                    base_dir=storage_dir,
                    timeout=30,
                    delay_range=(2.0, 5.0),
                    use_cache=True,
                )

                cls._alternative_finder = AlternativeSourceFinder(
                    scihub_downloader=scihub,
                    enable_scihub=enable_scihub,
                )

            # Orquestador que envuelve la cadena con lógica adicional
            oa_checker = ChainedOpenAccessChecker(
                checker_chain=cls._oa_checker_chain,
                skip_sources=["Scopus"],  # No gastar cuota si ya viene de Scopus
            )

            cls._fulltext_service_production = FullTextService(
                oa_checker=oa_checker,
                downloader=cls._http_downloader,
                alternative_finder=cls._alternative_finder,
                file_validator=cls.get_file_validator(),
                repository=cls.get_repository(),
            )

        return cls._fulltext_service_production

    # --------------------------------------------------------------------- #
    # Application services con persistencia
    # --------------------------------------------------------------------- #

    @classmethod
    def get_manual_study_service(cls) -> ManualStudyService:
        """
        Servicio para registro manual de estudios.
        """
        if cls._manual_study_service is None:
            cls._manual_study_service = ManualStudyService(
                repository=cls.get_repository()
            )
        return cls._manual_study_service

    @classmethod
    def get_manual_edit_service(cls) -> ManualEditService:
        """
        Servicio para edición manual de metadatos de estudios.
        """
        if cls._manual_edit_service is None:
            cls._manual_edit_service = ManualEditService(
                repository=cls.get_repository()
            )
        return cls._manual_edit_service

    @classmethod
    def get_consolidation_service(cls) -> ConsolidationService:
        """
        Servicio para consolidación automática de metadatos (Feature 3).

        De momento se inicializa sin conectores externos (modo safe/testing).
        En producción se pueden inyectar conectores reales desde aquí.
        """
        if cls._consolidation_service is None:
            connectors: Dict[str, Any] = {}  # TODO: inyectar Scopus/IEEE/Crossref cuando toque
            cls._consolidation_service = ConsolidationService(
                connectors=connectors,
                repository=cls.get_repository(),
            )
        return cls._consolidation_service

    @classmethod
    def get_enrichment_service(cls) -> ConsolidationService:
        """
        Alias para get_consolidation_service (compatibilidad con Facade).

        La Facade usa el término "enrichment" que es más amigable,
        pero internamente es el mismo ConsolidationService.
        """
        return cls.get_consolidation_service()

    # --------------------------------------------------------------------- #
    # Utilidades
    # --------------------------------------------------------------------- #

    @classmethod
    def reset(cls) -> None:
        """
        Resetea todas las instancias singleton del container.

        Útil para testing cuando necesitas "limpiar" el estado.
        """
        cls._repository = None

        cls._scopus_connector = None
        cls._ieee_connector = None
        cls._crossref_connector = None

        cls._file_validator = None
        cls._translation_service = None
        cls._discovery_service = None
        cls._preview_discovery_service = None
        cls._orchestrator = None

        cls._unpaywall_checker = None
        cls._crossref_checker = None
        cls._scopus_oa_checker = None
        cls._http_downloader = None
        cls._alternative_finder = None
        cls._fulltext_service_production = None
        cls._storage = None
        cls._manual_upload_app_service = None

        cls._manual_study_service = None
        cls._manual_edit_service = None
        cls._consolidation_service = None
