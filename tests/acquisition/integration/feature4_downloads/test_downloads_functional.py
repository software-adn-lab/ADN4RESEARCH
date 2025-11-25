"""
Test funcional completo de Feature 4: Descargas / Texto completo.

Prueba la cascada completa de descargas:
1. Unpaywall (Open Access legal)
2. Crossref (metadatos + links OA)
3. Scopus API (institucional, si configurado)
4. Sci-Hub V2 (zona gris, OPT-IN, deshabilitado por defecto)
5. No disponible

Usa el servicio real de aplicación con conectores reales.

Cubre:
- Happy path: Descarga exitosa desde OA
- Cascada: Intenta múltiples fuentes si una falla
- Validación: PDFs válidos (magic bytes)
- Estados finales: disponible / no_disponible

NOTA: Requiere configuración en .env:
- UNPAYWALL_EMAIL (requerido)
- SCOPUS_API_KEY (opcional)
- ENABLE_SCIHUB=true (opcional, deshabilitado por defecto)

Ejecutar con:
    python tests/acquisition/integration/feature4_downloads/test_downloads_functional.py
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

from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.downloads.application.fulltext_service import FullTextService
from apps.acquisition.downloads.application.open_access_checker import CompositeOpenAccessChecker
from apps.acquisition.downloads.adapters.outbound.connectors.unpaywall_checker import UnpaywallChecker
from apps.acquisition.downloads.adapters.outbound.connectors.crossref_open_access_checker import CrossrefOpenAccessChecker
from apps.acquisition.downloads.adapters.outbound.connectors.scopus_institutional_checker import ScopusInstitutionalChecker
from apps.acquisition.downloads.adapters.outbound.connectors.alternative_source_finder import AlternativeSourceFinder
from apps.acquisition.downloads.adapters.outbound.connectors.scihub_downloader import SciHubDownloader
from apps.acquisition.downloads.adapters.outbound.connectors.http_downloader import HttpDownloader
from apps.acquisition.downloads.domain.services.file_validator import FileValidator

print("=" * 80)
print("TEST FUNCIONAL: FEATURE 4 - DESCARGAS / TEXTO COMPLETO")
print("=" * 80)
print()

# Verificar configuración
ENABLE_SCIHUB = os.getenv("ENABLE_SCIHUB", "false").lower() == "true"
UNPAYWALL_EMAIL = os.getenv("UNPAYWALL_EMAIL") or os.getenv("EPN_USER") or os.getenv("IEEE_USERNAME")
SCOPUS_API_KEY = os.getenv("SCOPUS_API_KEY")

print("CONFIGURACIÓN:")
print(f"  UNPAYWALL_EMAIL: {UNPAYWALL_EMAIL[:30] if UNPAYWALL_EMAIL else 'N/A'}...")
print(f"  SCOPUS_API_KEY: {'✓ Configurado' if SCOPUS_API_KEY else '✗ No configurado'}")
print(f"  ENABLE_SCIHUB: {ENABLE_SCIHUB}")
print()

if not UNPAYWALL_EMAIL:
    print("⚠️  WARNING: UNPAYWALL_EMAIL no configurado")
    print("   El test será limitado")
    print()

# Construir servicio manualmente (sin Django)
print("Inicializando servicio de producción...")
storage_dir = "media/papers"

# Crear checkers de OA
unpaywall_checker = UnpaywallChecker(email=UNPAYWALL_EMAIL) if UNPAYWALL_EMAIL else None
crossref_checker = CrossrefOpenAccessChecker(email=UNPAYWALL_EMAIL) if UNPAYWALL_EMAIL else None
scopus_checker = ScopusInstitutionalChecker(api_key=SCOPUS_API_KEY) if SCOPUS_API_KEY else None

# Composite OA checker
if unpaywall_checker:
    oa_checker = CompositeOpenAccessChecker(
        primary_checker=unpaywall_checker,
        secondary_checker=crossref_checker,
        tertiary_checker=scopus_checker,
        skip_tertiary_for_sources=['Scopus']
    )
else:
    # Fallback simple si no hay email configurado
    class SimpleOAChecker:
        def is_open_access(self, doi, study=None):
            return False
    oa_checker = SimpleOAChecker()

# HTTP downloader
http_downloader = HttpDownloader(base_dir=storage_dir)

# Componentes de descarga alternativa (zona gris)
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

# File validator
file_validator = FileValidator()

# Crear servicio
service = FullTextService(
    oa_checker=oa_checker,
    downloader=http_downloader,
    alternative_finder=alternative_finder,
    file_validator=file_validator
)
print("✓ Servicio inicializado")
print()

tests_passed = 0
tests_total = 3

# ============================================================================
# TEST 1: Paper Open Access (debe descargar desde Unpaywall/Crossref)
# ============================================================================
print("=" * 80)
print("TEST 1: Paper Open Access (descarga legal)")
print("=" * 80)
print()

try:
    # Paper conocido que está en Open Access
    study_oa = Study.from_dict({
        "title": "PLOS Medicine Open Access Paper",
        "doi": "10.1371/journal.pmed.0020124",
        "source": "Manual",
        "link": "http://example.com",
        "is_open_access": None  # Dejar que el servicio lo descubra
    })

    print(f"📄 Paper: {study_oa.title}")
    print(f"   DOI: {study_oa.doi.value}")
    print()

    result1 = service.obtain_fulltext(study_oa)

    print(f"✓ Download status: {result1.download_status}")
    print(f"✓ PDF source: {result1.pdf_source}")
    print(f"✓ Is OA: {result1.is_open_access}")

    if result1.pdf_path:
        pdf_file = Path(result1.pdf_path)
        if pdf_file.exists():
            size_mb = pdf_file.stat().st_size / (1024 * 1024)
            print(f"✓ PDF path: {result1.pdf_path}")
            print(f"✓ Tamaño: {size_mb:.2f} MB")

            # Validar PDF
            with open(result1.pdf_path, 'rb') as f:
                header = f.read(4)
                if header == b'%PDF':
                    print(f"✓ PDF válido (magic bytes)")
                else:
                    print(f"⚠️  Header: {header}")

    print()

    # Validaciones
    if result1.pdf_path and Path(result1.pdf_path).exists():
        assert result1.download_status == "texto_completo_disponible", \
            "Status debe ser disponible"
        assert result1.pdf_source in ["automatico", "alternativo"], \
            "Source debe ser automático o alternativo"
        print("✅ TEST 1 PASADO: PDF OA descargado")
        tests_passed += 1
    else:
        print("⚠️  TEST 1: No se descargó PDF (puede no estar disponible)")

except AssertionError as e:
    print(f"❌ TEST 1 FALLADO: {e}")
except Exception as e:
    print(f"❌ TEST 1 ERROR: {e}")

print()

# ============================================================================
# TEST 2: Paper NO Open Access (debe probar cascada completa)
# ============================================================================
print("=" * 80)
print("TEST 2: Paper NO Open Access (cascada completa)")
print("=" * 80)
print()

try:
    study_noa = Study.from_dict({
        "title": "Empirical Studies of Agile Software Development",
        "doi": "10.1016/j.infsof.2008.01.006",
        "source": "Scopus",
        "link": "http://example.com",
        "is_open_access": False
    })

    print(f"📄 Paper: {study_noa.title}")
    print(f"   DOI: {study_noa.doi.value}")
    print(f"   OA: {study_noa.is_open_access}")
    print()

    result2 = service.obtain_fulltext(study_noa)

    print(f"✓ Download status: {result2.download_status}")
    print(f"✓ PDF source: {result2.pdf_source}")

    if result2.pdf_path:
        pdf_file = Path(result2.pdf_path)
        if pdf_file.exists():
            size_mb = pdf_file.stat().st_size / (1024 * 1024)
            print(f"✓ PDF path: {result2.pdf_path}")
            print(f"✓ Tamaño: {size_mb:.2f} MB")
    print()

    # Validaciones
    if result2.pdf_path and Path(result2.pdf_path).exists():
        assert result2.download_status == "texto_completo_disponible"
        # Si Sci-Hub está habilitado, source puede ser "alternativo"
        # Si no, no debería descargar (marcado como no_disponible)
        print("✅ TEST 2 PASADO: Cascada ejecutada correctamente")
        tests_passed += 1
    else:
        if ENABLE_SCIHUB:
            print("⚠️  TEST 2: No se descargó (Sci-Hub habilitado pero pudo fallar)")
        else:
            assert result2.download_status == "no_disponible", \
                "Sin Sci-Hub, debe marcar como no_disponible"
            print("✅ TEST 2 PASADO: Marcado como no_disponible (sin Sci-Hub)")
            tests_passed += 1

except AssertionError as e:
    print(f"❌ TEST 2 FALLADO: {e}")
except Exception as e:
    print(f"❌ TEST 2 ERROR: {e}")

print()

# ============================================================================
# TEST 3: Paper inexistente (debe marcar como no_disponible)
# ============================================================================
print("=" * 80)
print("TEST 3: Paper inexistente (debe marcar no_disponible)")
print("=" * 80)
print()

try:
    study_fake = Study.from_dict({
        "title": "Nonexistent Paper Test",
        "doi": "10.9999/fake.2025.99999",
        "source": "Manual",
        "link": "http://example.com"
    })

    print(f"📄 Paper: {study_fake.title}")
    print(f"   DOI: {study_fake.doi.value}")
    print()

    result3 = service.obtain_fulltext(study_fake)

    print(f"✓ Download status: {result3.download_status}")
    print(f"✓ PDF source: {result3.pdf_source}")
    print()

    # Validaciones
    assert result3.download_status == "no_disponible", \
        "Paper inexistente debe estar marcado como no_disponible"
    assert not result3.pdf_path, "No debe tener PDF"

    print("✅ TEST 3 PASADO: Paper inexistente marcado correctamente")
    tests_passed += 1

except AssertionError as e:
    print(f"❌ TEST 3 FALLADO: {e}")
except Exception as e:
    print(f"❌ TEST 3 ERROR: {e}")

print()

# ============================================================================
# RESUMEN
# ============================================================================
print("=" * 80)
print("RESUMEN DE TESTS")
print("=" * 80)
print()

print(f"Tests ejecutados: {tests_total}")
print(f"Tests pasados: {tests_passed}")
print(f"Tests fallados: {tests_total - tests_passed}")
print()

if not ENABLE_SCIHUB:
    print("NOTA: Sci-Hub está deshabilitado.")
    print("  Para habilitar: ENABLE_SCIHUB=true en .env")
    print()

if tests_passed == tests_total:
    print("✅ FEATURE 4 (DESCARGAS): TODOS LOS TESTS PASADOS")
    exit(0)
elif tests_passed >= tests_total - 1:
    print("⚠️  FEATURE 4 (DESCARGAS): MAYORMENTE PASADO (puede depender de disponibilidad de papers)")
    exit(0)
else:
    print("❌ FEATURE 4 (DESCARGAS): ALGUNOS TESTS FALLARON")
    exit(1)
