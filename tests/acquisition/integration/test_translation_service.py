"""
Test de integracion para TranslationService.

Prueba la traduccion REAL de estrategias a Scopus e IEEE.
No usa mocks - ejecuta el servicio completo.

Ejecutar con:
    python tests/acquisition/integration/test_translation_service.py
"""
import sys
from pathlib import Path

# Fix encoding Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.acquisition.translation.domain.models import NormalizedStrategy
from apps.acquisition.translation.application.translation_service import TranslationService

print("=" * 80)
print("TEST TRANSLATION SERVICE (FEATURE 1)")
print("=" * 80)
print()

# Estrategia de prueba (la misma del Feature 1 BDD)
STRATEGY_DATA = {
    "strategy_id": "test_integration_2024",
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

print("=" * 80)
print("TEST 1: Traduccion a Scopus")
print("=" * 80)
print()

try:
    result_scopus = service.translate(strategy, "Scopus")

    print(f"Status: {result_scopus['status']}")
    print(f"Target: {result_scopus['target']}")
    print(f"Warnings: {result_scopus['warnings']}")
    print()
    print("Query generada:")
    print("-" * 60)
    print(result_scopus['query'])
    print("-" * 60)
    print()
    print("Trace:")
    print(f"  - trace_id: {result_scopus['trace']['trace_id'][:8]}...")
    print(f"  - steps: {result_scopus['trace']['steps_applied']}")
    print(f"  - rules: {len(result_scopus['trace']['rules_applied'])} reglas aplicadas")
    print()

    # Validaciones
    assert result_scopus['status'] == "Done", "Status debe ser Done"
    assert result_scopus['query'], "Query no debe estar vacia"
    assert "TITLE-ABS-KEY" in result_scopus['query'], "Debe usar TITLE-ABS-KEY de Scopus"
    assert "PUBYEAR" in result_scopus['query'], "Debe incluir filtro de anio"
    print("OK Scopus: Todas las validaciones pasaron")

except Exception as e:
    print(f"ERROR en Scopus: {e}")

print()
print("=" * 80)
print("TEST 2: Traduccion a IEEE Xplore")
print("=" * 80)
print()

try:
    result_ieee = service.translate(strategy, "IEEE Xplore")

    print(f"Status: {result_ieee['status']}")
    print(f"Target: {result_ieee['target']}")
    print(f"Warnings: {result_ieee['warnings']}")
    print()
    print("Query generada:")
    print("-" * 60)
    print(result_ieee['query'])
    print("-" * 60)
    print()

    # Validaciones
    assert result_ieee['status'] == "Done", "Status debe ser Done"
    assert result_ieee['query'], "Query no debe estar vacia"
    # IEEE usa comillas y parentesis, no TITLE-ABS-KEY
    assert "machine learning" in result_ieee['query'].lower(), "Debe incluir terminos"
    print("OK IEEE: Todas las validaciones pasaron")

except Exception as e:
    print(f"ERROR en IEEE: {e}")

print()
print("=" * 80)
print("TEST 3: Target no soportado")
print("=" * 80)
print()

try:
    service.translate(strategy, "GoogleScholar")
    print("ERROR: Debio lanzar excepcion")
except Exception as e:
    print(f"OK: Excepcion esperada: {type(e).__name__}")

print()
print("=" * 80)
print("TEST COMPLETADO")
print("=" * 80)
