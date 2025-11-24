"""
DIAGNÓSTICO PROFUNDO: ¿Qué métodos de conexión están funcionando?

Este test valida:
1. ¿IEEE /rest/search funciona?
2. ¿IEEE Playwright funciona?
3. ¿Scopus API oficial funciona?
4. ¿Scopus Playwright fallback funciona?
5. ¿Autenticación bvirtual funciona?

Ejecutar con:
    python tests/acquisition/integration/test_diagnostic_connectors.py
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

print("=" * 80)
print("🔬 DIAGNÓSTICO PROFUNDO: Métodos de Conexión")
print("=" * 80)
print()

# ============================================================================
# CONFIGURACIÓN
# ============================================================================
SCOPUS_API_KEY = os.getenv("SCOPUS_API_KEY")
EPN_USER = os.getenv("EPN_USER")
EPN_PASS = os.getenv("EPN_PASS")

print("CREDENCIALES DISPONIBLES:")
print(f"  SCOPUS_API_KEY: {'✅' if SCOPUS_API_KEY else '❌'}")
print(f"  EPN_USER: {'✅ ' + EPN_USER if EPN_USER else '❌'}")
print(f"  EPN_PASS: {'✅ Configurada' if EPN_PASS else '❌'}")
print()

if not EPN_USER or not EPN_PASS:
    print("❌ Se requieren credenciales EPN para este test")
    sys.exit(1)

# ============================================================================
# TEST 1: Scopus API Oficial (api.elsevier.com)
# ============================================================================
print("=" * 80)
print("TEST 1: Scopus API Oficial (Método Preferido)")
print("=" * 80)
print()

if not SCOPUS_API_KEY:
    print("❌ SALTADO: Sin SCOPUS_API_KEY")
    print()
    scopus_api_works = False
else:
    try:
        from apps.acquisition.discovery.adapters.outbound.connectors.scopus_connector import ScopusConnector

        connector = ScopusConnector(
            api_key=SCOPUS_API_KEY,
            username=EPN_USER,
            password=EPN_PASS,
            headless=True
        )

        print("🔍 Buscando: 'machine learning' (max: 3 resultados)")
        print()

        results = list(connector.search('TITLE-ABS-KEY("machine learning")', max_results=3))

        if results:
            print(f"✅ FUNCIONANDO: {len(results)} resultados obtenidos")
            print()
            print("Primer resultado:")
            first = results[0]
            print(f"  Título: {first.get('title', 'N/A')[:60]}...")
            print(f"  DOI: {first.get('doi', 'N/A')}")
            print(f"  Año: {first.get('year', 'N/A')}")
            print(f"  Open Access: {first.get('is_open_access', 'N/A')}")
            scopus_api_works = True
        else:
            print("⚠️  Sin resultados (pero API respondió)")
            scopus_api_works = False

        connector.close()

    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        scopus_api_works = False

print()

# ============================================================================
# TEST 2: Scopus Playwright Fallback
# ============================================================================
print("=" * 80)
print("TEST 2: Scopus Playwright Fallback (APIs internas)")
print("=" * 80)
print()

try:
    from apps.acquisition.discovery.adapters.outbound.connectors.scopus_playwright_connector import ScopusPlaywrightConnector

    print("🔍 Buscando con Playwright: 'machine learning' (max: 2)")
    print()

    connector = ScopusPlaywrightConnector(
        username=EPN_USER,
        password=EPN_PASS,
        headless=True
    )

    results = list(connector.search('machine learning', max_results=2))

    if results:
        print(f"✅ FUNCIONANDO: {len(results)} resultados obtenidos")
        print()
        print("Primer resultado:")
        first = results[0]
        print(f"  Título: {first.get('title', 'N/A')[:60]}...")
        print(f"  DOI: {first.get('doi', 'N/A')}")
        scopus_playwright_works = True
    else:
        print("⚠️  Sin resultados")
        scopus_playwright_works = False

except Exception as e:
    print(f"❌ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    scopus_playwright_works = False

print()

# ============================================================================
# TEST 3: IEEE /rest/search (API interna REST)
# ============================================================================
print("=" * 80)
print("TEST 3: IEEE /rest/search (API interna vía EZproxy)")
print("=" * 80)
print()

try:
    from apps.acquisition.discovery.adapters.outbound.connectors.ieee_connector import IeeeConnector

    print("🔍 Intentando búsqueda con /rest/search")
    print("   (Método: Session Manager + requests)")
    print()

    connector = IeeeConnector(
        username=EPN_USER,
        password=EPN_PASS,
        headless=True,
        prefer_playwright=False  # Forzar uso de /rest/search
    )

    results = list(connector.search('machine learning', max_results=3))

    if results:
        print(f"✅ FUNCIONANDO: {len(results)} resultados obtenidos")
        print()
        print("Primer resultado:")
        first = results[0]
        print(f"  Título: {first.get('title', 'N/A')[:60]}...")
        print(f"  DOI: {first.get('doi', 'N/A')}")
        print(f"  Open Access: {first.get('is_open_access', 'N/A')}")
        ieee_rest_works = True
    else:
        print("⚠️  Sin resultados")
        ieee_rest_works = False

except Exception as e:
    print(f"❌ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    ieee_rest_works = False

print()

# ============================================================================
# TEST 4: IEEE Playwright (scraping HTML)
# ============================================================================
print("=" * 80)
print("TEST 4: IEEE Playwright (scraping HTML directo)")
print("=" * 80)
print()

try:
    from apps.acquisition.discovery.adapters.outbound.connectors.ieee_connector import IeeeConnector

    print("🔍 Intentando búsqueda con Playwright")
    print("   (Método: Playwright directo)")
    print()

    connector = IeeeConnector(
        username=EPN_USER,
        password=EPN_PASS,
        headless=True,
        prefer_playwright=True  # Forzar uso de Playwright
    )

    results = list(connector.search('machine learning', max_results=2))

    if results:
        print(f"✅ FUNCIONANDO: {len(results)} resultados obtenidos")
        print()
        print("Primer resultado:")
        first = results[0]
        print(f"  Título: {first.get('title', 'N/A')[:60]}...")
        print(f"  DOI: {first.get('doi', 'N/A')}")
        ieee_playwright_works = True
    else:
        print("⚠️  Sin resultados")
        ieee_playwright_works = False

except Exception as e:
    print(f"❌ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    ieee_playwright_works = False

print()

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print("=" * 80)
print("📊 RESUMEN EJECUTIVO")
print("=" * 80)
print()

print("MÉTODOS DE CONEXIÓN:")
print()

# Scopus
print("Scopus:")
if scopus_api_works:
    print("  ✅ API Oficial (Método Preferido) - FUNCIONANDO")
else:
    print("  ❌ API Oficial - FALLÓ")

if scopus_playwright_works:
    print("  ✅ Playwright Fallback - FUNCIONANDO")
else:
    print("  ⚠️  Playwright Fallback - FALLÓ")

print()

# IEEE
print("IEEE:")
if ieee_rest_works:
    print("  ✅ /rest/search (API interna) - FUNCIONANDO")
else:
    print("  ⚠️  /rest/search - FALLÓ (puede ser anti-bot)")

if ieee_playwright_works:
    print("  ✅ Playwright (scraping HTML) - FUNCIONANDO")
else:
    print("  ⚠️  Playwright - FALLÓ")

print()
print("=" * 80)
print("ANÁLISIS")
print("=" * 80)
print()

total_methods = 4
working_methods = sum([
    scopus_api_works,
    scopus_playwright_works,
    ieee_rest_works,
    ieee_playwright_works
])

print(f"Métodos funcionando: {working_methods}/{total_methods}")
print()

if working_methods >= 3:
    print("✅ SISTEMA ROBUSTO: Múltiples métodos de conexión funcionando")
    print("   Tu sistema está listo para producción")
elif working_methods >= 2:
    print("⚠️  SISTEMA FUNCIONAL: Al menos 2 métodos funcionando")
    print("   Recomendado ejecutar desde red EPN para mejor acceso")
elif working_methods >= 1:
    print("⚠️  SISTEMA LIMITADO: Solo 1 método funcionando")
    print("   Considera ejecutar desde red EPN o VPN institucional")
else:
    print("❌ PROBLEMA: Ningún método funcionando")
    print("   Verifica credenciales y conectividad")

print()

# Recomendaciones específicas
print("RECOMENDACIONES:")
print()

if not scopus_api_works and SCOPUS_API_KEY:
    print("  ⚠️  Scopus API falló:")
    print("     - Verifica que la API key sea válida")
    print("     - Revisa si la cuota no está agotada")
    print()

if not ieee_rest_works:
    print("  ⚠️  IEEE /rest/search falló:")
    print("     - Posible detección anti-bot (HTTP 418)")
    print("     - Ejecutar desde red EPN puede ayudar")
    print("     - El fallback Playwright debería compensar")
    print()

if not ieee_playwright_works:
    print("  ⚠️  IEEE Playwright falló:")
    print("     - Verifica credenciales EPN")
    print("     - Puede haber problema con formulario de login")
    print()

if scopus_api_works:
    print("  ✅ Scopus API funcionando: Este es tu método principal")
    print()

if ieee_playwright_works or ieee_rest_works:
    print("  ✅ IEEE operativo: Al menos un método funciona")
    print()

print("=" * 80)
print("DIAGNÓSTICO COMPLETADO")
print("=" * 80)
