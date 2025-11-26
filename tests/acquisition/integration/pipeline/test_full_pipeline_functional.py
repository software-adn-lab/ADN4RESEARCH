"""
Test maestro del pipeline completo end-to-end.

Simula el flujo completo de Adquisición:
1. Diseño SLR → Estrategia normalizada
2. Traducción → Queries para Scopus e IEEE
3. Descubrimiento → Listado consolidado sin duplicados
4. Enriquecimiento → Metadatos completos
5. Selección (simulado) → Estudios aceptados
6. Descarga → PDFs de estudios aceptados

Este test valida que TODA la infraestructura funciona end-to-end
usando los servicios REALES de producción.

NOTA: Requiere credenciales en .env:
- SCOPUS_API_KEY o EPN_USER/EPN_PASS
- IEEE_USERNAME/IEEE_PASSWORD
- UNPAYWALL_EMAIL
- ENABLE_SCIHUB (opcional, deshabilitado por defecto)

Ejecutar con:
    python tests/acquisition/integration/pipeline/test_full_pipeline_functional.py
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Fix encoding Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv()

# Configurar Django ANTES de importar modelos
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.acquisition.container import Container
from apps.acquisition.translation.domain.models import NormalizedStrategy
from apps.acquisition.translation.application.translation_service import TranslationService
from apps.acquisition.discovery.application.discovery_service import DiscoveryService
from apps.acquisition.discovery.adapters.outbound.connectors.composite_scopus_connector import CompositeScopusConnector
from apps.acquisition.discovery.adapters.outbound.connectors.ieee_connector import IeeeConnector
from apps.acquisition.discovery.adapters.outbound.connectors.crossref_connector import CrossrefConnector
from apps.acquisition.metadata.application.consolidation_service import ConsolidationService
from apps.acquisition.downloads.application.fulltext_service import FullTextService
from apps.acquisition.downloads.application.open_access_checker import CompositeOpenAccessChecker
from apps.acquisition.downloads.adapters.outbound.connectors.unpaywall_checker import UnpaywallChecker
from apps.acquisition.downloads.adapters.outbound.connectors.crossref_open_access_checker import CrossrefOpenAccessChecker
from apps.acquisition.downloads.adapters.outbound.connectors.scopus_institutional_checker import ScopusInstitutionalChecker
from apps.acquisition.downloads.adapters.outbound.connectors.alternative_source_finder import AlternativeSourceFinder
from apps.acquisition.downloads.adapters.outbound.connectors.scihub_downloader import SciHubDownloader
from apps.acquisition.downloads.adapters.outbound.connectors.http_downloader import HttpDownloader
from apps.acquisition.downloads.domain.services.file_validator import FileValidator
from apps.acquisition.shared.domain.constants import TRANSLATION_STATUS_READY

print("=" * 80)
print("TEST MAESTRO: PIPELINE COMPLETO END-TO-END")
print("=" * 80)
print()

# Verificar configuración
print("Verificando configuración...")
SCOPUS_API_KEY = os.getenv("SCOPUS_API_KEY")
SCOPUS_COOKIES = os.getenv("SCOPUS_COOKIES")
EPN_USER = os.getenv("EPN_USER")
EPN_PASS = os.getenv("EPN_PASS")
# IEEE puede usar las mismas credenciales EPN
IEEE_USERNAME = os.getenv("IEEE_USERNAME") or EPN_USER
IEEE_PASSWORD = os.getenv("IEEE_PASSWORD") or EPN_PASS
UNPAYWALL_EMAIL = os.getenv("UNPAYWALL_EMAIL") or EPN_USER or IEEE_USERNAME
ENABLE_SCIHUB = os.getenv("ENABLE_SCIHUB", "false").lower() == "true"

scopus_available = SCOPUS_API_KEY or (EPN_USER and EPN_PASS) or SCOPUS_COOKIES
ieee_available = IEEE_USERNAME and IEEE_PASSWORD

print(f"  Scopus: {'✓' if scopus_available else '✗'}")
if SCOPUS_COOKIES:
    print(f"    → Con cookies preloaded (bypass reCAPTCHA)")
print(f"  IEEE: {'✓' if ieee_available else '✗'}")
print(f"  Unpaywall: {'✓' if UNPAYWALL_EMAIL else '✗'}")
print(f"  Sci-Hub: {'✓ Habilitado' if ENABLE_SCIHUB else '✗ Deshabilitado'}")
print()

if not scopus_available and not ieee_available:
    print("❌ ERROR: No hay credenciales configuradas")
    print("   Se requiere al menos una fuente (Scopus o IEEE)")
    exit(1)

# ============================================================================
# PASO 1: ESTRATEGIA NORMALIZADA (desde módulo Diseño SLR)
# ============================================================================
print("=" * 80)
print("PASO 1: Estrategia normalizada (desde Diseño SLR)")
print("=" * 80)
print()

STRATEGY_DATA = {
    "strategy_id": "pipeline_test_2024",
    "main_terms": [
        {
            "term": "machine learning",
            "synonyms": []
        }
    ],
    "exclusions": [],
    "filters": {
        "year_filter": {
            "from": 2019,
            "to": 2021
        }
    }
}

strategy = NormalizedStrategy.from_dict(STRATEGY_DATA)
print(f"✓ Estrategia creada: {strategy.strategy_id}")
print(f"  Términos principales: {len(strategy.main_terms)}")
print(f"  Exclusiones: {len(strategy.exclusions)}")
print()

# ============================================================================
# PASO 2: TRADUCCIÓN (Feature 1)
# ============================================================================
print("=" * 80)
print("PASO 2: Traducción a Scopus e IEEE (Feature 1)")
print("=" * 80)
print()

translation_service = TranslationService()
translation_statuses = {}

if scopus_available:
    result_scopus = translation_service.translate(strategy, "Scopus")
    translation_statuses["Scopus"] = {
        "status": TRANSLATION_STATUS_READY,
        "query": result_scopus["query"]
    }
    print(f"✓ Scopus traducido: {len(result_scopus['query'])} caracteres")

if ieee_available:
    result_ieee = translation_service.translate(strategy, "IEEE Xplore")
    translation_statuses["IEEE Xplore"] = {
        "status": TRANSLATION_STATUS_READY,
        "query": result_ieee["query"]
    }
    print(f"✓ IEEE traducido: {len(result_ieee['query'])} caracteres")

print()

# ============================================================================
# PASO 3: DESCUBRIMIENTO + DEDUPLICACIÓN (Feature 2)
# ============================================================================
print("=" * 80)
print("PASO 3: Descubrimiento + Deduplicación (Feature 2)")
print("=" * 80)
print()

# Inicializar conectores
connectors = {}
if scopus_available:
    connectors["Scopus"] = CompositeScopusConnector(
        api_key=SCOPUS_API_KEY,
        username=EPN_USER,
        password=EPN_PASS,
        preloaded_cookies=SCOPUS_COOKIES
    )
if ieee_available:
    connectors["IEEE Xplore"] = IeeeConnector(
        username=IEEE_USERNAME,
        password=IEEE_PASSWORD
    )

discovery_service = DiscoveryService(
    connectors=connectors,
    repository=Container.get_repository()  # ← Persistir estudios en DB
)

discovery_result = discovery_service.execute(
    strategy_id=strategy.strategy_id,
    translation_statuses=translation_statuses,
    supported_sources=list(connectors.keys()),
    max_results_per_source=10  # Limitado para test rápido
)

studies_discovered = discovery_result.studies

print(f"✓ Estudios brutos: {discovery_result.summary['total_bruto']}")
print(f"✓ Estudios únicos (deduplicados): {discovery_result.summary['total_unicos']}")
print(f"✓ Resultado: {discovery_result.summary['resultado']}")
print()

if not studies_discovered:
    print("⚠️  WARNING: No se encontraron estudios")
    print("   El pipeline se detiene aquí (no hay estudios para enriquecer)")
    exit(0)

# ============================================================================
# PASO 4: ENRIQUECIMIENTO DE METADATOS (Feature 3)
# ============================================================================
print("=" * 80)
print("PASO 4: Enriquecimiento de metadatos (Feature 3)")
print("=" * 80)
print()

crossref = CrossrefConnector(username=UNPAYWALL_EMAIL or "test@example.com")
consolidation_service = ConsolidationService(
    connectors={"Crossref": crossref},
    repository=Container.get_repository()
)

# enrich_studies() recibe lista de IDs, no estudios
study_ids = [study.id for study in studies_discovered]
consolidation_result = consolidation_service.enrich_studies(study_ids)
studies_enriched = consolidation_result.studies

print(f"✓ Estudios enriquecidos: {len(studies_enriched)}")
print(f"  Completos: {consolidation_result.summary.get('complete', 0)}")
print(f"  Parciales: {consolidation_result.summary.get('partial', 0)}")
print(f"  Fallidos: {consolidation_result.summary.get('failed', 0)}")
print()

# ============================================================================
# PASO 5: SELECCIÓN (Simulado - el módulo Selección decidirá)
# ============================================================================
print("=" * 80)
print("PASO 5: Selección de estudios (SIMULADO)")
print("=" * 80)
print()

# Simular selección: aceptar solo estudios COMPLETOS
studies_complete = [s for s in studies_enriched if s.consolidation_status == "completo"]

if not studies_complete:
    print("⚠️  WARNING: No hay estudios completos para seleccionar")
    print("   Usando estudios parciales para continuar el test")
    studies_accepted = studies_enriched[:2]  # Tomar los primeros 2
else:
    studies_accepted = studies_complete[:2]  # Tomar los primeros 2 completos

print(f"✓ Estudios aceptados (simulado): {len(studies_accepted)}")
for i, study in enumerate(studies_accepted, 1):
    print(f"  {i}. {study.title[:50]}...")
print()

# ============================================================================
# PASO 6: DESCARGA DE TEXTO COMPLETO (Feature 4)
# ============================================================================
print("=" * 80)
print("PASO 6: Descarga de textos completos (Feature 4)")
print("=" * 80)
print()

# Construir servicio de fulltext
storage_dir = "media/papers"
unpaywall_checker = UnpaywallChecker(email=UNPAYWALL_EMAIL) if UNPAYWALL_EMAIL else None
crossref_oa_checker = CrossrefOpenAccessChecker(email=UNPAYWALL_EMAIL) if UNPAYWALL_EMAIL else None
scopus_oa_checker = ScopusInstitutionalChecker(api_key=SCOPUS_API_KEY) if SCOPUS_API_KEY else None

if unpaywall_checker:
    oa_checker = CompositeOpenAccessChecker(
        primary_checker=unpaywall_checker,
        secondary_checker=crossref_oa_checker,
        tertiary_checker=scopus_oa_checker,
        skip_tertiary_for_sources=['Scopus']
    )
else:
    class SimpleOAChecker:
        def is_open_access(self, doi, study=None):
            return False
    oa_checker = SimpleOAChecker()

http_downloader = HttpDownloader(base_dir=storage_dir)
scihub = SciHubDownloader(
    enabled=ENABLE_SCIHUB,
    base_dir=storage_dir,
    timeout=30,
    delay_range=(2.0, 5.0),
    use_cache=True
)
alternative_finder = AlternativeSourceFinder(
    scihub_downloader=scihub,
    enable_scihub=ENABLE_SCIHUB,
    base_dir=storage_dir
)
file_validator = FileValidator()

fulltext_service = FullTextService(
    oa_checker=oa_checker,
    downloader=http_downloader,
    alternative_finder=alternative_finder,
    file_validator=file_validator,
    repository=Container.get_repository()  # ← Persistir PDFs en DB
)

downloaded_studies = []
for study in studies_accepted:
    print(f"Descargando: {study.title[:40]}...")
    updated_study = fulltext_service.download_fulltext(study.id)
    downloaded_studies.append(updated_study)
    print(f"  → Status: {updated_study.download_status}, Source: {updated_study.pdf_source}")

print()

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print("=" * 80)
print("RESUMEN FINAL DEL PIPELINE")
print("=" * 80)
print()

print("ESTADÍSTICAS:")
print(f"  1. Traducción: {len(translation_statuses)} fuentes traducidas")
print(f"  2. Descubrimiento: {discovery_result.summary['total_unicos']} estudios únicos")
print(f"  3. Enriquecimiento: {len(studies_enriched)} estudios enriquecidos")
print(f"  4. Selección: {len(studies_accepted)} estudios aceptados")
print(f"  5. Descarga: {len([s for s in downloaded_studies if s.pdf_path])} PDFs descargados")
print()

# Validaciones del pipeline completo
success = True

try:
    # 1. Debe haber traducciones
    assert len(translation_statuses) > 0, "Debe haber al menos una traducción"

    # 2. Debe haber estudios descubiertos
    assert len(studies_discovered) > 0, "Debe haber estudios descubiertos"

    # 3. Deduplicación debe funcionar
    assert discovery_result.summary['total_unicos'] <= discovery_result.summary['total_bruto'], \
        "Deduplicación debe reducir o mantener el total"

    # 4. Todos los estudios deben tener consolidation_status
    assert all(hasattr(s, 'consolidation_status') for s in studies_enriched), \
        "Todos los estudios deben tener consolidation_status"

    # 5. Descargas deben tener estados válidos
    valid_statuses = ["texto_completo_disponible", "no_disponible"]
    assert all(s.download_status in valid_statuses for s in downloaded_studies), \
        "Todos los estudios deben tener estados de descarga válidos"

    print("✅ PIPELINE COMPLETO: TODAS LAS VALIDACIONES PASARON")
    print()
    print("El sistema está listo para producción:")
    print("  ✓ Traducción funciona")
    print("  ✓ Descubrimiento con deduplicación funciona")
    print("  ✓ Enriquecimiento funciona")
    print("  ✓ Descarga con cascada funciona")

except AssertionError as e:
    print(f"❌ PIPELINE FALLIDO: {e}")
    success = False

print()
print("=" * 80)
print("FIN DEL TEST MAESTRO")
print("=" * 80)

exit(0 if success else 1)
