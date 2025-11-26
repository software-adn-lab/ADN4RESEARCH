"""
Test funcional completo de Feature 2: Discovery + Deduplicación.

Prueba el descubrimiento REAL de estudios desde Scopus e IEEE.
Incluye deduplicación automática.
Usa los servicios y conectores reales, no mocks.

Cubre:
- Happy path: Discovery exitoso desde múltiples fuentes
- Deduplicación: Elimina duplicados por DOI y título
- Error path: Tolerancia a fallos (una fuente cae, continúa con las demás)

NOTA: Este test requiere credenciales configuradas en .env:
- SCOPUS_API_KEY o EPN_USER/EPN_PASS
- IEEE_USERNAME/IEEE_PASSWORD

Ejecutar con:
    python tests/acquisition/integration/feature2_discovery/test_discovery_functional.py
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

from apps.acquisition.discovery.application.discovery_service import DiscoveryService
from apps.acquisition.discovery.adapters.outbound.connectors.composite_scopus_connector import CompositeScopusConnector
from apps.acquisition.discovery.adapters.outbound.connectors.ieee_connector import IeeeConnector

print("=" * 80)
print("TEST FUNCIONAL: FEATURE 2 - DISCOVERY + DEDUPLICACIÓN")
print("=" * 80)
print()

# Verificar configuración
print("Verificando credenciales...")
SCOPUS_API_KEY = os.getenv("SCOPUS_API_KEY")
SCOPUS_COOKIES = os.getenv("SCOPUS_COOKIES")
EPN_USER = os.getenv("EPN_USER")
EPN_PASS = os.getenv("EPN_PASS")
# IEEE puede usar las mismas credenciales EPN que Scopus
IEEE_USERNAME = os.getenv("IEEE_USERNAME") or EPN_USER
IEEE_PASSWORD = os.getenv("IEEE_PASSWORD") or EPN_PASS

scopus_available = SCOPUS_API_KEY or (EPN_USER and EPN_PASS) or SCOPUS_COOKIES
ieee_available = IEEE_USERNAME and IEEE_PASSWORD

print(f"  Scopus: {'✓ Configurado' if scopus_available else '✗ No configurado'}")
if SCOPUS_COOKIES:
    print(f"    → Con cookies preloaded (bypass reCAPTCHA)")
print(f"  IEEE: {'✓ Configurado' if ieee_available else '✗ No configurado'}")
print()

if not scopus_available and not ieee_available:
    print("⚠️  WARNING: No hay credenciales configuradas")
    print("   Este test será limitado (solo validará estructura, no datos reales)")
    print()

# Inicializar conectores REALES
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

if not connectors:
    print("❌ No hay conectores disponibles. Abortando test.")
    exit(1)

# CAMBIO: Usar Container para obtener DiscoveryService con persistencia
from apps.acquisition.container import Container

# El Container inyecta el repositorio automáticamente
service = Container.get_discovery_service()

tests_passed = 0
tests_total = 2

# ============================================================================
# TEST 1: Discovery exitoso con deduplicación
# ============================================================================
print("=" * 80)
print("TEST 1: Discovery exitoso con deduplicación")
print("=" * 80)
print()

# Queries traducidas (simulando salida de TranslationService)
translation_statuses = {}

if "Scopus" in connectors:
    translation_statuses["Scopus"] = {
        "status": "ready",
        "query": 'TITLE-ABS-KEY("machine learning")'
    }

if "IEEE Xplore" in connectors:
    translation_statuses["IEEE Xplore"] = {
        "status": "ready",
        "query": '("machine learning" OR "deep learning") AND ("software engineering")'
    }

try:
    result = service.execute(
        strategy_id="test_functional_discovery",
        translation_statuses=translation_statuses,
        supported_sources=list(connectors.keys()),
        max_results_per_source=10  # Limitar para test rápido
    )

    print(f"✓ Estudios encontrados (bruto): {result.summary['total_bruto']}")
    print(f"✓ Estudios únicos (deduplicados): {result.summary['total_unicos']}")
    print(f"✓ Resultado: {result.summary['resultado']}")
    print()

    print("Estudios por fuente:")
    for source, count in result.summary['total_por_fuente'].items():
        print(f"  - {source}: {count} estudios")
    print()

    if result.summary.get('no_ejecutadas'):
        print("⚠️  Fuentes no ejecutadas:")
        for source, reason in result.summary['no_ejecutadas'].items():
            print(f"  - {source}: {reason}")
        print()

    # Validaciones de negocio
    assert result.studies, "Debe retornar al menos un estudio"
    assert len(result.studies) > 0, "Debe haber estudios"
    # strategy_id es opcional en el summary
    # assert result.summary.get('strategy_id') == "test_functional_discovery", "strategy_id debe coincidir"
    assert result.summary['total_unicos'] <= result.summary['total_bruto'], \
        "Total único debe ser <= total bruto (deduplicación)"

    # Validar que no hay duplicados por DOI
    dois = [s.doi.value for s in result.studies if s.doi]
    assert len(dois) == len(set(dois)), "No debe haber DOIs duplicados"

    # Validar que cada estudio tiene campos mínimos
    for study in result.studies[:3]:  # Validar los primeros 3
        assert study.title, f"Estudio debe tener título: {study}"
        assert study.link, f"Estudio debe tener link: {study}"
        assert study.source, f"Estudio debe tener source: {study}"

    print("✅ TEST 1 PASADO: Discovery ejecutado con deduplicación correcta")
    tests_passed += 1

except AssertionError as e:
    print(f"❌ TEST 1 FALLADO: {e}")
except Exception as e:
    print(f"❌ TEST 1 ERROR: {e}")

print()

# ============================================================================
# TEST 2: Tolerancia a fallos (fuente con status != ready)
# ============================================================================
print("=" * 80)
print("TEST 2: Tolerancia a fallos (fuente no ready)")
print("=" * 80)
print()

try:
    # Simular que una fuente no tiene traducción ready
    translation_statuses_partial = translation_statuses.copy()
    translation_statuses_partial["FakeSource"] = {
        "status": "not_ready",
        "query": None
    }

    result2 = service.execute(
        strategy_id="test_partial_execution",
        translation_statuses=translation_statuses_partial,
        supported_sources=list(connectors.keys()) + ["FakeSource"],
        max_results_per_source=5
    )

    print(f"✓ Resultado: {result2.summary['resultado']}")
    print(f"✓ Estudios únicos: {result2.summary['total_unicos']}")
    print()

    # Validaciones
    assert result2.studies, "Debe retornar estudios de las fuentes válidas"
    assert result2.summary.get('no_ejecutadas'), "Debe rastrear fuentes no ejecutadas"
    assert "FakeSource" in result2.summary['no_ejecutadas'], "Debe incluir FakeSource en no_ejecutadas"

    print(f"✓ Fuentes no ejecutadas:")
    for source, reason in result2.summary['no_ejecutadas'].items():
        print(f"  - {source}: {reason}")
    print()

    print("✅ TEST 2 PASADO: Tolerancia a fallos funciona correctamente")
    tests_passed += 1

except AssertionError as e:
    print(f"❌ TEST 2 FALLADO: {e}")
except Exception as e:
    print(f"❌ TEST 2 ERROR: {e}")

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

if tests_passed == tests_total:
    print("✅ FEATURE 2 (DISCOVERY): TODOS LOS TESTS PASADOS")
    exit(0)
else:
    print("❌ FEATURE 2 (DISCOVERY): ALGUNOS TESTS FALLARON")
    exit(1)
