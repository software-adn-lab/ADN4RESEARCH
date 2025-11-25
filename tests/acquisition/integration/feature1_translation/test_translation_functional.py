"""
Test funcional completo de Feature 1: Traducción de estrategias.

Prueba la traducción REAL de estrategias a Scopus e IEEE Xplore.
Usa los servicios reales de aplicación, no mocks.

Cubre:
- Happy path: Traducción exitosa a Scopus e IEEE
- Error path: Target no soportado
- Validaciones: Estructura de respuesta, warnings, trace

Ejecutar con:
    python tests/acquisition/integration/feature1_translation/test_translation_functional.py
"""
import sys
from pathlib import Path

# Fix encoding Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.acquisition.translation.domain.models import NormalizedStrategy
from apps.acquisition.translation.application.translation_service import TranslationService
from apps.acquisition.translation.application.exceptions import InvalidTargetError

print("=" * 80)
print("TEST FUNCIONAL: FEATURE 1 - TRADUCCIÓN DE ESTRATEGIAS")
print("=" * 80)
print()

# Estrategia de prueba (alineada con Feature 1 BDD)
STRATEGY_DATA = {
    "strategy_id": "test_functional_2024",
    "main_terms": [
        {
            "term": "machine learning",
            "synonyms": ["deep learning", "ML", "artificial intelligence"]
        },
        {
            "term": "software engineering",
            "synonyms": ["software development", "software quality"]
        },
        {
            "term": "bug prediction",
            "synonyms": ["defect prediction", "fault prediction"]
        }
    ],
    "exclusions": [
        "hardware testing",
        "gaming",
        "mobile applications"
    ],
    "filters": {
        "year": {
            "from": 2020,
            "to": 2024
        }
    }
}

# Inicializar servicio
service = TranslationService()
strategy = NormalizedStrategy.from_dict(STRATEGY_DATA)

tests_passed = 0
tests_total = 3

# ============================================================================
# TEST 1: Traducción a Scopus (Happy Path)
# ============================================================================
print("=" * 80)
print("TEST 1: Traducción a Scopus (Happy Path)")
print("=" * 80)
print()

try:
    result_scopus = service.translate(strategy, "Scopus")

    print(f"✓ Status: {result_scopus['status']}")
    print(f"✓ Target: {result_scopus['target']}")
    print(f"✓ Warnings: {result_scopus['warnings']}")
    print()
    print("Query generada:")
    print("-" * 60)
    print(result_scopus['query'][:200] + "..." if len(result_scopus['query']) > 200 else result_scopus['query'])
    print("-" * 60)
    print()

    # Validaciones de negocio
    assert result_scopus['status'] == "Done", "Status debe ser Done"
    assert result_scopus['target'] == "Scopus", "Target debe ser Scopus"
    assert result_scopus['query'], "Query no debe estar vacía"
    assert "TITLE-ABS-KEY" in result_scopus['query'], "Debe usar sintaxis TITLE-ABS-KEY de Scopus"
    assert "PUBYEAR" in result_scopus['query'], "Debe incluir filtro de año con PUBYEAR"
    assert result_scopus['warnings'] == [], "Scopus no debe tener warnings (soporta filtros de año)"
    assert 'trace' in result_scopus, "Debe incluir trace de ejecución"
    assert result_scopus['trace']['steps_applied'], "Trace debe tener steps aplicados"

    print("✅ TEST 1 PASADO: Scopus traducido correctamente")
    tests_passed += 1

except AssertionError as e:
    print(f"❌ TEST 1 FALLADO: {e}")
except Exception as e:
    print(f"❌ TEST 1 ERROR: {e}")

print()

# ============================================================================
# TEST 2: Traducción a IEEE Xplore (Happy Path con Warning)
# ============================================================================
print("=" * 80)
print("TEST 2: Traducción a IEEE Xplore (Happy Path con Warning)")
print("=" * 80)
print()

try:
    result_ieee = service.translate(strategy, "IEEE Xplore")

    print(f"✓ Status: {result_ieee['status']}")
    print(f"✓ Target: {result_ieee['target']}")
    print(f"✓ Warnings: {result_ieee['warnings']}")
    print()
    print("Query generada:")
    print("-" * 60)
    print(result_ieee['query'][:200] + "..." if len(result_ieee['query']) > 200 else result_ieee['query'])
    print("-" * 60)
    print()

    # Validaciones de negocio
    assert result_ieee['status'] == "Done", "Status debe ser Done"
    assert result_ieee['target'] == "IEEE Xplore", "Target debe ser IEEE Xplore"
    assert result_ieee['query'], "Query no debe estar vacía"
    assert "TITLE-ABS-KEY" not in result_ieee['query'], "IEEE no usa TITLE-ABS-KEY"
    assert "PUBYEAR" not in result_ieee['query'], "IEEE no usa PUBYEAR"
    assert "machine learning" in result_ieee['query'].lower(), "Debe incluir términos de búsqueda"

    # IEEE debe tener warning sobre año (Feature 1 BDD especifica esto)
    assert len(result_ieee['warnings']) > 0, "IEEE debe tener warnings sobre filtros no soportados"
    assert any("2020" in w or "2024" in w or "año" in w.lower() for w in result_ieee['warnings']), \
        "Warning debe mencionar filtros de año"

    print("✅ TEST 2 PASADO: IEEE traducido correctamente con warnings")
    tests_passed += 1

except AssertionError as e:
    print(f"❌ TEST 2 FALLADO: {e}")
except Exception as e:
    print(f"❌ TEST 2 ERROR: {e}")

print()

# ============================================================================
# TEST 3: Target no soportado (Error Path)
# ============================================================================
print("=" * 80)
print("TEST 3: Target no soportado (Error Path)")
print("=" * 80)
print()

try:
    result_invalid = service.translate(strategy, "GoogleScholar")
    print(f"❌ TEST 3 FALLADO: Debió lanzar InvalidTargetError")

except InvalidTargetError as e:
    print(f"✓ Excepción esperada capturada: {type(e).__name__}")
    print(f"✓ Mensaje: {str(e)}")
    print()
    print("✅ TEST 3 PASADO: InvalidTargetError lanzado correctamente")
    tests_passed += 1

except Exception as e:
    print(f"❌ TEST 3 FALLADO: Excepción incorrecta: {type(e).__name__}: {e}")

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
    print("✅ FEATURE 1 (TRADUCCIÓN): TODOS LOS TESTS PASADOS")
    exit(0)
else:
    print("❌ FEATURE 1 (TRADUCCIÓN): ALGUNOS TESTS FALLARON")
    exit(1)
