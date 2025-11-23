"""
Mock factories para Feature 4: Downloads/Full-text availability.

ESTRATEGIA:
- Las factories crean servicios de aplicación con mocks inyectados
- Los mocks simulan comportamiento determinista basado en convenciones de DOI
- Esto permite que los steps BDD sean limpios (solo llaman a la factory)

CONVENCIONES DE TEST (Fixtures deterministas):
- DOI "10.1000/open.access" → Tratado como Open Access
- DOI con "paywall" → Tratado como cerrado → busca alternativa
- DOI "10.1000/missing" → No se encuentra en ninguna fuente
"""

from unittest.mock import MagicMock


def build_fulltext_service_with_mocks():
    """
    Factory que crea FullTextService con mocks inyectados.

    Configuración de mocks (fixtures deterministas):
    - OA Checker: Solo DOI "10.1000/open.access" es Open Access
    - Downloader: Descarga exitosa para estudios OA
    - Alternative Finder: Encuentra alternativa para DOIs con "paywall"

    Returns:
        FullTextService con dependencias mockeadas

    Ejemplo de uso (en steps BDD):
        service = build_fulltext_service_with_mocks()
        result_study = service.obtain_fulltext(study)
    """
    # WISHFUL THINKING: Import del servicio de aplicación
    from apps.acquisition.downloads.application.fulltext_service import FullTextService

    # ========================================================================
    # Mock 1: Open Access Checker (simula Unpaywall API)
    # ========================================================================
    mock_oa_checker = MagicMock()

    def is_open_access_side_effect(doi):
        """
        Simula la lógica de Unpaywall:
        - Devuelve True solo si el DOI es "10.1000/open.access"
        - En producción, esto llamaría a la API de Unpaywall
        """
        if doi is None:
            return False
        return doi.value == "10.1000/open.access"

    mock_oa_checker.is_open_access.side_effect = is_open_access_side_effect

    # ========================================================================
    # Mock 2: Downloader (simula descarga HTTP + escritura de archivo)
    # ========================================================================
    mock_downloader = MagicMock()

    def download_side_effect(study):
        """
        Simula descarga exitosa para estudios Open Access.

        En producción, esto:
        1. Haría requests.get(url)
        2. Escribiría bytes a disco
        3. Retornaría la ruta del archivo

        Returns:
            str: Ruta simulada del PDF descargado
            None: Si no se pudo descargar
        """
        if study.doi and "open.access" in study.doi.value:
            # Simula ruta de archivo descargado
            safe_doi = study.doi.value.replace("/", "_")
            return f"/tmp/downloads/{safe_doi}.pdf"
        return None

    mock_downloader.download.side_effect = download_side_effect

    # ========================================================================
    # Mock 3: Alternative Source Finder (simula scraping/repositorios)
    # ========================================================================
    mock_alt_finder = MagicMock()

    def find_alternative_side_effect(study):
        """
        Simula búsqueda en fuentes alternativas (Unpaywall, CORE, ResearchGate).

        Convención de test:
        - DOI con "paywall" → encuentra alternativa
        - Otros DOIs → no encuentra

        En producción, esto:
        1. Buscaría en múltiples repositorios
        2. Intentaría descargar desde la mejor fuente
        3. Retornaría ruta del archivo o None

        Returns:
            str: Ruta simulada del PDF desde fuente alternativa
            None: Si no se encontró en ninguna fuente alternativa
        """
        if study.doi and "paywall" in study.doi.value:
            # Simula que encontró el PDF en una fuente alternativa
            return "/tmp/downloads/alternative_source.pdf"
        return None

    mock_alt_finder.find_and_download.side_effect = find_alternative_side_effect

    # ========================================================================
    # Construir y retornar servicio con mocks inyectados
    # ========================================================================
    return FullTextService(
        oa_checker=mock_oa_checker,
        downloader=mock_downloader,
        alternative_finder=mock_alt_finder,
    )


def build_manual_upload_service_with_mocks():
    """
    Factory que crea ManualUploadService con validador REAL.

    NOTA: A diferencia de FullTextService, ManualUploadService NO necesita mocks
    porque FileValidator es lógica INTERNA (no externa):
    - No hace peticiones HTTP
    - Solo lee magic bytes del archivo
    - Es rápido y determinista

    Esta factory existe solo para mantener consistencia con el patrón de los steps,
    pero usa el FileValidator real.

    Si en el futuro necesitas probar escenarios de validación fallida,
    podrías crear una factory separada: build_manual_upload_service_with_invalid_file()

    Returns:
        ManualUploadService con FileValidator REAL

    Ejemplo de uso (en steps BDD):
        service = build_manual_upload_service_with_mocks()
        result_study = service.attach_file(study, "/path/to/file.pdf")
    """
    # WISHFUL THINKING: Import del servicio de aplicación
    from apps.acquisition.downloads.application.manual_upload_service import ManualUploadService
    from apps.acquisition.downloads.domain.services.file_validator import FileValidator

    # ========================================================================
    # Usar FileValidator REAL (no mockeado)
    # ========================================================================
    # FileValidator es lógica interna que:
    # - Lee magic bytes (%PDF)
    # - Valida estructura básica del PDF
    # - No tiene dependencias externas
    validator = FileValidator()

    # ========================================================================
    # Construir y retornar servicio
    # ========================================================================
    return ManualUploadService(file_validator=validator)
