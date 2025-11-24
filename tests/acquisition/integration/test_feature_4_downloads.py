"""
Test de integración para Feature 4 (Descargas de PDFs).

Este test valida el flujo completo de descarga automática:
1. Descarga directa desde hint de discovery (IEEE OA)
2. Cascada de checkers OA (Unpaywall -> Crossref -> Scopus)
3. Marcado como no_disponible cuando no hay fuente

IMPORTANTE: Requiere credenciales reales en .env:
    - UNPAYWALL_EMAIL (o EPN_USER/IEEE_USERNAME como fallback)
    - SCOPUS_API_KEY (opcional, para checker institucional)
    - PAPERS_STORAGE_DIR (opcional, default: media/papers)

Ejecutar con:
    python tests/acquisition/integration/test_feature_4_downloads.py
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Fix encoding Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv()

# Imports del sistema (sin Django)
from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.downloads.application.fulltext_service import FullTextService
from apps.acquisition.downloads.application.open_access_checker import CompositeOpenAccessChecker
from apps.acquisition.downloads.adapters.outbound.connectors.unpaywall_checker import UnpaywallChecker
from apps.acquisition.downloads.adapters.outbound.connectors.crossref_open_access_checker import CrossrefOpenAccessChecker
from apps.acquisition.downloads.adapters.outbound.connectors.scopus_institutional_checker import ScopusInstitutionalChecker
from apps.acquisition.downloads.adapters.outbound.connectors.http_downloader import HttpDownloader
from apps.acquisition.downloads.adapters.outbound.connectors.alternative_source_finder import AlternativeSourceFinder
from apps.acquisition.downloads.domain.services.file_validator import FileValidator

print("=" * 80)
print("TEST FEATURE 4 - DESCARGAS (PRODUCCIÓN)")
print("=" * 80)
print()

# Verificar credenciales
EMAIL = os.getenv("UNPAYWALL_EMAIL") or os.getenv("EPN_USER") or os.getenv("IEEE_USERNAME")
SCOPUS_KEY = os.getenv("SCOPUS_API_KEY")
STORAGE_DIR = os.getenv("PAPERS_STORAGE_DIR", "media/papers")

if not EMAIL:
    print("❌ ERROR: Se requiere UNPAYWALL_EMAIL (o EPN_USER/IEEE_USERNAME)")
    sys.exit(1)

print(f"✅ Email configurado: {EMAIL}")
print(f"✅ Storage dir: {STORAGE_DIR}")
if SCOPUS_KEY:
    print(f"✅ Scopus API Key configurada")
else:
    print(f"⚠️  Scopus API Key NO configurada (checker institucional deshabilitado)")
print()

# ============================================================================
# INICIALIZACIÓN DEL SERVICIO
# ============================================================================
print("=" * 80)
print("INICIALIZACIÓN")
print("=" * 80)
print()

try:
    # Inicializar servicios manualmente (sin Container/Django)
    unpaywall = UnpaywallChecker(email=EMAIL)
    crossref = CrossrefOpenAccessChecker(email=EMAIL)
    scopus_oa = ScopusInstitutionalChecker(api_key=SCOPUS_KEY) if SCOPUS_KEY else None

    oa_checker = CompositeOpenAccessChecker(
        primary_checker=unpaywall,
        secondary_checker=crossref,
        tertiary_checker=scopus_oa,
        skip_tertiary_for_sources=['Scopus']
    )

    downloader = HttpDownloader(base_dir=STORAGE_DIR)
    alternative_finder = AlternativeSourceFinder()
    file_validator = FileValidator()

    service = FullTextService(
        oa_checker=oa_checker,
        downloader=downloader,
        alternative_finder=alternative_finder,
        file_validator=file_validator
    )

    print("✅ FullTextService (producción) inicializado correctamente")
except Exception as e:
    print(f"❌ ERROR inicializando servicio: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# ============================================================================
# CASO 1: Paper con HINT de Discovery (IEEE OA)
# ============================================================================
print("=" * 80)
print("CASO 1: Paper IEEE con Hint OA (pdf_url desde discovery)")
print("=" * 80)
print()

# DOI real de IEEE Open Access
# Ejemplo: 10.1109/ACCESS.2019.2927063 (IEEE Access es OA)
study_ieee_hint = Study.from_dict({
    "title": "Test IEEE OA with Hint",
    "link": "https://ieeexplore.ieee.org/document/8758919",
    "source": "IEEE Xplore",
    "doi": "10.1109/ACCESS.2019.2927063",
    "status": "enriched",
    # Simulamos que el IeeeConnector ya nos dio estos valores
    "is_open_access": True,
    "pdf_url": "https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=8758919"
})

print(f"📄 Study: {study_ieee_hint.title}")
print(f"   DOI: {study_ieee_hint.doi.value if study_ieee_hint.doi else 'N/A'}")
print(f"   OA Hint: {study_ieee_hint.is_open_access}")
print(f"   PDF URL: {study_ieee_hint.pdf_url}")
print()

try:
    result_1 = service.obtain_fulltext(study_ieee_hint)
    print(f"✅ Resultado: {result_1.download_status}")
    if result_1.pdf_path:
        pdf_file = Path(result_1.pdf_path)
        if pdf_file.exists():
            size_kb = pdf_file.stat().st_size / 1024
            print(f"   PDF descargado: {result_1.pdf_path}")
            print(f"   Tamaño: {size_kb:.2f} KB")
            print(f"   Fuente: {result_1.pdf_source}")
        else:
            print(f"   ⚠️  PDF reportado pero no existe en disco")
    else:
        print(f"   ⚠️  No se obtuvo PDF (esperado si hay problemas de red/paywall)")
except Exception as e:
    print(f"❌ ERROR: {e}")

print()

# ============================================================================
# CASO 2: Paper Open Access (sin hint, debe detectarlo Unpaywall)
# ============================================================================
print("=" * 80)
print("CASO 2: Paper OA sin Hint (detectado por Unpaywall/Crossref)")
print("=" * 80)
print()

# DOI conocido OA: PLOS ONE (siempre OA)
study_oa_no_hint = Study.from_dict({
    "title": "Test OA without Hint",
    "link": "http://example.com",
    "source": "Scopus",
    "doi": "10.1371/journal.pone.0000308",  # PLOS ONE
    "status": "enriched",
    # NO tiene is_open_access ni pdf_url
})

print(f"📄 Study: {study_oa_no_hint.title}")
print(f"   DOI: {study_oa_no_hint.doi.value if study_oa_no_hint.doi else 'N/A'}")
print(f"   OA Hint: {study_oa_no_hint.is_open_access}")
print(f"   PDF URL: {study_oa_no_hint.pdf_url}")
print()

try:
    result_2 = service.obtain_fulltext(study_oa_no_hint)
    print(f"✅ Resultado: {result_2.download_status}")
    if result_2.pdf_path:
        pdf_file = Path(result_2.pdf_path)
        if pdf_file.exists():
            size_kb = pdf_file.stat().st_size / 1024
            print(f"   PDF descargado: {result_2.pdf_path}")
            print(f"   Tamaño: {size_kb:.2f} KB")
            print(f"   Fuente: {result_2.pdf_source}")
        else:
            print(f"   ⚠️  PDF reportado pero no existe en disco")
    else:
        print(f"   ⚠️  No se obtuvo PDF")

    # Validar que Unpaywall enriqueció el estudio
    if result_2.is_open_access:
        print(f"   ✅ OA detectado por checkers")
    if result_2.pdf_url:
        print(f"   ✅ PDF URL enriquecida: {result_2.pdf_url[:60]}...")

except Exception as e:
    print(f"❌ ERROR: {e}")

print()

# ============================================================================
# CASO 3: Paper NO Open Access (paywall)
# ============================================================================
print("=" * 80)
print("CASO 3: Paper NO OA (Paywall, debe marcar como no_disponible)")
print("=" * 80)
print()

# DOI conocido de Nature (paywall seguro)
study_paywall = Study.from_dict({
    "title": "Test Paywall Paper",
    "link": "http://example.com",
    "source": "Scopus",
    "doi": "10.1038/nature12373",  # Nature (paywall)
    "status": "enriched",
})

print(f"📄 Study: {study_paywall.title}")
print(f"   DOI: {study_paywall.doi.value if study_paywall.doi else 'N/A'}")
print()

try:
    result_3 = service.obtain_fulltext(study_paywall)
    print(f"✅ Resultado: {result_3.download_status}")

    if result_3.download_status == "no_disponible":
        print(f"   ✅ Correctamente marcado como no_disponible (requiere carga manual)")
    elif result_3.pdf_path:
        print(f"   ⚠️  SORPRESA: Se descargó un PDF (¿fuente alternativa?)")
        print(f"      PDF: {result_3.pdf_path}")
        print(f"      Fuente: {result_3.pdf_source}")

except Exception as e:
    print(f"❌ ERROR: {e}")

print()

# ============================================================================
# CASO 4: Paper sin DOI (debe fallar rápido)
# ============================================================================
print("=" * 80)
print("CASO 4: Paper sin DOI (debe marcar como no_disponible)")
print("=" * 80)
print()

study_no_doi = Study.from_dict({
    "title": "Test Paper without DOI",
    "link": "http://example.com",
    "source": "Scopus",
    "status": "enriched",
    # NO tiene DOI
})

print(f"📄 Study: {study_no_doi.title}")
print(f"   DOI: {study_no_doi.doi}")
print()

try:
    result_4 = service.obtain_fulltext(study_no_doi)
    print(f"✅ Resultado: {result_4.download_status}")

    if result_4.download_status == "no_disponible":
        print(f"   ✅ Correctamente marcado como no_disponible")

except Exception as e:
    print(f"❌ ERROR: {e}")

print()

# ============================================================================
# RESUMEN
# ============================================================================
print("=" * 80)
print("RESUMEN DE VALIDACIONES")
print("=" * 80)
print()

checks = {
    "Caso 1 (IEEE hint)": result_1.download_status if 'result_1' in locals() else "ERROR",
    "Caso 2 (OA sin hint)": result_2.download_status if 'result_2' in locals() else "ERROR",
    "Caso 3 (Paywall)": result_3.download_status if 'result_3' in locals() else "ERROR",
    "Caso 4 (Sin DOI)": result_4.download_status if 'result_4' in locals() else "ERROR",
}

for caso, status in checks.items():
    print(f"  {caso}: {status}")

print()

# Validaciones esperadas
expected = {
    "Caso 1 (IEEE hint)": "texto_completo_disponible",  # Debería bajar desde IEEE
    "Caso 2 (OA sin hint)": "texto_completo_disponible",  # Debería bajar desde Unpaywall
    "Caso 3 (Paywall)": "no_disponible",  # No debería encontrar fuente
    "Caso 4 (Sin DOI)": "no_disponible",  # No tiene DOI, no puede buscar
}

passed = sum(1 for caso, status in checks.items() if status == expected[caso])
total = len(checks)

print(f"Resultado: {passed}/{total} casos cumplieron expectativas")
print()

if passed == total:
    print("✅ TODOS LOS TESTS PASARON")
else:
    print("⚠️  ALGUNOS TESTS NO CUMPLIERON EXPECTATIVAS")
    print()
    print("NOTAS:")
    print("  - Caso 1 puede fallar si IEEE cambió su estructura o hay problemas de red")
    print("  - Caso 2 puede fallar si Unpaywall API está caído o el DOI no está indexado")
    print("  - Casos 3 y 4 deberían SIEMPRE pasar (son fallos esperados)")

print()
print("=" * 80)
print("TEST COMPLETADO")
print("=" * 80)
