"""
Test de integración para validar extracción de Open Access en ScopusConnector.

Este test verifica que el conector de Scopus (API y Playwright fallback)
extrae correctamente los campos is_open_access y pdf_url desde el discovery.

IMPORTANTE: Requiere credenciales reales en .env:
    - SCOPUS_API_KEY (para API oficial)
    - EPN_USER / EPN_PASS (para fallback Playwright)

Ejecutar con:
    python tests/acquisition/integration/test_scopus_oa_extraction.py
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

# Imports del sistema
from apps.acquisition.discovery.adapters.outbound.connectors.scopus_connector import ScopusConnector

print("=" * 80)
print("TEST SCOPUS - EXTRACCIÓN DE OPEN ACCESS (DISCOVERY)")
print("=" * 80)
print()

# Verificar credenciales
SCOPUS_API_KEY = os.getenv("SCOPUS_API_KEY")
EPN_USER = os.getenv("EPN_USER")
EPN_PASS = os.getenv("EPN_PASS")

if not SCOPUS_API_KEY:
    print("❌ WARN: SCOPUS_API_KEY no configurada - solo fallback Playwright disponible")
if not EPN_USER or not EPN_PASS:
    print("❌ WARN: EPN_USER/EPN_PASS no configuradas - fallback Playwright deshabilitado")

if not SCOPUS_API_KEY and not EPN_USER:
    print("❌ ERROR: Se requiere SCOPUS_API_KEY o EPN_USER/EPN_PASS")
    sys.exit(1)

print()

# ============================================================================
# TEST: Búsqueda con query que devuelva papers OA
# ============================================================================
print("=" * 80)
print("CASO: Búsqueda de papers Open Access")
print("=" * 80)
print()

# Query que probablemente devuelva papers OA (machine learning en journals OA)
query = 'TITLE-ABS-KEY("machine learning") AND PUBYEAR > 2022'
max_results = 10

print(f"Query: {query}")
print(f"Max resultados: {max_results}")
print()

try:
    # Inicializar conector
    connector = ScopusConnector(
        username=EPN_USER,
        password=EPN_PASS,
        api_key=SCOPUS_API_KEY,
        headless=True,
        rate_limit=1.0
    )

    print("Ejecutando búsqueda...")
    print()

    results = list(connector.search(query, max_results=max_results))

    if not results:
        print("⚠️  No se obtuvieron resultados")
        sys.exit(1)

    print(f"✅ Obtenidos {len(results)} resultados")
    print()

    # Analizar resultados
    oa_stats = {
        "total": len(results),
        "oa_confirmed": 0,
        "oa_false": 0,
        "oa_null": 0,
        "with_pdf_url": 0,
        "with_doi": 0
    }

    print("=" * 80)
    print("ANÁLISIS DE RESULTADOS")
    print("=" * 80)
    print()

    for i, result in enumerate(results, 1):
        title = result.get('title', 'N/A')
        doi = result.get('doi')
        is_oa = result.get('is_open_access')
        pdf_url = result.get('pdf_url')

        print(f"[{i}] {title[:60]}...")
        print(f"    DOI: {doi if doi else 'N/A'}")
        print(f"    Open Access: {is_oa}")
        print(f"    PDF URL: {pdf_url if pdf_url else 'N/A'}")

        # Estadísticas
        if is_oa is True:
            oa_stats["oa_confirmed"] += 1
        elif is_oa is False:
            oa_stats["oa_false"] += 1
        else:
            oa_stats["oa_null"] += 1

        if pdf_url:
            oa_stats["with_pdf_url"] += 1
        if doi:
            oa_stats["with_doi"] += 1

        print()

    # Resumen estadístico
    print("=" * 80)
    print("RESUMEN ESTADÍSTICO")
    print("=" * 80)
    print()

    print(f"Total de resultados: {oa_stats['total']}")
    print(f"  Con DOI: {oa_stats['with_doi']} ({oa_stats['with_doi'] / oa_stats['total'] * 100:.1f}%)")
    print()
    print(f"Open Access detectado:")
    print(f"  ✅ OA confirmado (True): {oa_stats['oa_confirmed']} ({oa_stats['oa_confirmed'] / oa_stats['total'] * 100:.1f}%)")
    print(f"  ❌ NO OA (False): {oa_stats['oa_false']} ({oa_stats['oa_false'] / oa_stats['total'] * 100:.1f}%)")
    print(f"  ⚠️  No determinado (None): {oa_stats['oa_null']} ({oa_stats['oa_null'] / oa_stats['total'] * 100:.1f}%)")
    print()
    print(f"Con PDF URL: {oa_stats['with_pdf_url']} ({oa_stats['with_pdf_url'] / oa_stats['total'] * 100:.1f}%)")
    print()

    # ========================================================================
    # VALIDACIONES
    # ========================================================================
    print("=" * 80)
    print("VALIDACIONES")
    print("=" * 80)
    print()

    checks = []
    checks_passed = 0

    # Check 1: Todos los resultados tienen el campo is_open_access
    check1 = all('is_open_access' in r for r in results)
    checks.append(("Todos los resultados tienen campo 'is_open_access'", check1))
    if check1:
        checks_passed += 1

    # Check 2: Todos los resultados tienen el campo pdf_url
    check2 = all('pdf_url' in r for r in results)
    checks.append(("Todos los resultados tienen campo 'pdf_url'", check2))
    if check2:
        checks_passed += 1

    # Check 3: Al menos 1 paper OA detectado (estadísticamente probable)
    check3 = oa_stats['oa_confirmed'] > 0
    checks.append(("Al menos 1 paper OA detectado", check3))
    if check3:
        checks_passed += 1

    # Check 4: Papers OA tienen pdf_url
    check4 = True
    for result in results:
        if result.get('is_open_access') is True:
            if not result.get('pdf_url'):
                check4 = False
                break
    checks.append(("Papers OA tienen pdf_url", check4))
    if check4:
        checks_passed += 1

    # Mostrar resultados
    for description, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {description}")

    print()
    print(f"Resultado: {checks_passed}/{len(checks)} validaciones pasaron")
    print()

    # ========================================================================
    # CONCLUSIÓN
    # ========================================================================
    if checks_passed == len(checks):
        print("🎉 ✅ TODOS LOS TESTS PASARON")
        print()
        print("Conclusión:")
        print("  - ScopusConnector extrae is_open_access correctamente")
        print("  - Papers OA tienen pdf_url para descarga en Feature 4")
        print("  - La integración Discovery -> Downloads está lista")
    else:
        print("⚠️  ALGUNOS TESTS FALLARON")
        print()
        print("Posibles causas:")
        print("  - La API de Scopus no devolvió campos OA (cambio en API)")
        print("  - El query no devolvió papers OA (problema de búsqueda)")
        print("  - Problema de extracción en _normalize_api_result")

    print()
    connector.close()

except Exception as e:
    print(f"❌ ERROR CRÍTICO: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=" * 80)
print("TEST COMPLETADO")
print("=" * 80)
