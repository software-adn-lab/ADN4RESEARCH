"""
Test funcional completo de Feature 3: Enriquecimiento de metadatos.

Prueba la consolidación REAL de metadatos desde Crossref.
Usa el servicio real de aplicación, no mocks.

Cubre:
- Happy path: Enriquecimiento exitoso de estudios incompletos
- Normalización: Limpieza de DOI, autores, títulos
- Validación: Completitud de metadatos (completo/parcial/fallido)

NOTA: Este test NO requiere credenciales (Crossref es público)

Ejecutar con:
    python tests/acquisition/integration/feature3_metadata/test_metadata_enrichment_functional.py
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

from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.metadata.application.consolidation_service import ConsolidationService
from apps.acquisition.discovery.adapters.outbound.connectors.crossref_connector import CrossrefConnector

print("=" * 80)
print("TEST FUNCIONAL: FEATURE 3 - ENRIQUECIMIENTO DE METADATOS")
print("=" * 80)
print()

# Inicializar servicio REAL
crossref = CrossrefConnector(username="test@example.com")
service = ConsolidationService(connectors={"Crossref": crossref})

tests_passed = 0
tests_total = 3

# ============================================================================
# TEST 1: Enriquecimiento de estudio incompleto (Happy Path)
# ============================================================================
print("=" * 80)
print("TEST 1: Enriquecimiento de estudio incompleto")
print("=" * 80)
print()

try:
    # Estudio incompleto: solo título y link (como vendría de Discovery)
    study_incomplete = Study.from_dict({
        "title": "Empirical Studies of Agile Software Development: A Systematic Review",
        "link": "http://example.com",
        "source": "Scopus",
        "doi": None,  # Falta DOI
        "year": None,  # Falta año
        "authors": None  # Faltan autores
    })

    print(f"Antes del enriquecimiento:")
    print(f"  - DOI: {study_incomplete.doi}")
    print(f"  - Año: {study_incomplete.year}")
    print(f"  - Autores: {study_incomplete.authors}")
    print()

    # Consolidar
    result = service.consolidate([study_incomplete])

    # Obtener estudio enriquecido
    enriched = result.studies[0]

    print(f"Después del enriquecimiento:")
    print(f"  - DOI: {enriched.doi}")
    print(f"  - Año: {enriched.year}")
    print(f"  - Autores: {enriched.authors[:50] if enriched.authors else None}...")
    print(f"  - Consolidation status: {enriched.consolidation_status}")
    print()

    # Validaciones
    assert enriched.consolidation_status in ["completo", "parcial", "fallido"], \
        "Debe tener status de consolidación"

    # Si Crossref encontró algo, debería haber mejorado al menos un campo
    if enriched.consolidation_status != "fallido":
        assert enriched.doi or enriched.year or enriched.authors, \
            "Al menos un campo debe estar enriquecido"

    print("✅ TEST 1 PASADO: Enriquecimiento funciona")
    tests_passed += 1

except AssertionError as e:
    print(f"❌ TEST 1 FALLADO: {e}")
except Exception as e:
    print(f"❌ TEST 1 ERROR: {e}")

print()

# ============================================================================
# TEST 2: Normalización de DOI
# ============================================================================
print("=" * 80)
print("TEST 2: Normalización de DOI")
print("=" * 80)
print()

try:
    # Estudio con DOI malformado
    study_dirty_doi = Study.from_dict({
        "title": "Test Paper",
        "link": "http://example.com",
        "source": "Manual",
        "doi": "https://doi.org/10.1016/j.infsof.2008.01.006",  # DOI con prefijo
        "year": 2008,
        "authors": None
    })

    print(f"DOI original: {study_dirty_doi.doi.value}")

    result2 = service.consolidate([study_dirty_doi])
    normalized = result2.studies[0]

    print(f"DOI normalizado: {normalized.doi.value}")
    print()

    # Validaciones
    assert normalized.doi, "DOI no debe perderse"
    assert not normalized.doi.value.startswith("https://"), \
        "DOI debe estar normalizado (sin https://)"
    assert "10.1016" in normalized.doi.value, "DOI debe mantener su valor"

    print("✅ TEST 2 PASADO: Normalización de DOI funciona")
    tests_passed += 1

except AssertionError as e:
    print(f"❌ TEST 2 FALLADO: {e}")
except Exception as e:
    print(f"❌ TEST 2 ERROR: {e}")

print()

# ============================================================================
# TEST 3: Batch de múltiples estudios (tolerancia a fallos)
# ============================================================================
print("=" * 80)
print("TEST 3: Batch de múltiples estudios")
print("=" * 80)
print()

try:
    # Batch de 3 estudios: 2 válidos, 1 sin DOI
    studies_batch = [
        Study.from_dict({
            "title": "Valid Paper 1",
            "link": "http://example.com/1",
            "source": "Scopus",
            "doi": "10.1016/j.infsof.2008.01.006"
        }),
        Study.from_dict({
            "title": "Paper sin DOI",
            "link": "http://example.com/2",
            "source": "Manual",
            "doi": None  # Sin DOI (a enriquecer)
        }),
        Study.from_dict({
            "title": "Valid Paper 2",
            "link": "http://example.com/3",
            "source": "IEEE Xplore",
            "doi": None
        })
    ]

    result3 = service.consolidate(studies_batch)

    print(f"Estudios procesados: {len(result3.studies)}")
    print(f"Resumen:")
    for i, study in enumerate(result3.studies, 1):
        print(f"  {i}. Status: {study.consolidation_status}")
    print()

    # Validaciones
    assert len(result3.studies) == 3, "Debe retornar los 3 estudios (tolerancia a fallos)"
    assert all(hasattr(s, 'consolidation_status') for s in result3.studies), \
        "Todos deben tener consolidation_status"

    print("✅ TEST 3 PASADO: Batch con tolerancia a fallos funciona")
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

if tests_passed == tests_total:
    print("✅ FEATURE 3 (ENRIQUECIMIENTO): TODOS LOS TESTS PASADOS")
    exit(0)
else:
    print("❌ FEATURE 3 (ENRIQUECIMIENTO): ALGUNOS TESTS FALLARON")
    exit(1)
