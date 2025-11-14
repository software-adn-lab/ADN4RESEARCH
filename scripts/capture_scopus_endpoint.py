"""
Script para capturar el endpoint de búsqueda de Scopus (similar a TEST 3 para IEEE).

Este script:
1. Se autentica en Scopus vía EZproxy
2. Ejecuta una búsqueda de prueba
3. Captura todas las peticiones HTTP (especialmente XHR/Fetch)
4. Identifica el endpoint que retorna resultados de búsqueda

Uso:
    python scripts/capture_scopus_endpoint.py

IMPORTANTE: Ejecutar desde la RED de la universidad (o con VPN) para evitar problemas de autenticación.
"""
from playwright.sync_api import sync_playwright
import json
import time
import sys
from pathlib import Path

print("=" * 80)
print("CAPTURA DE ENDPOINT DE SCOPUS")
print("=" * 80)
print()
print("Este script captura las peticiones HTTP durante una búsqueda en Scopus")
print("para identificar el endpoint de búsqueda.")
print()
print("⚠️  IMPORTANTE: El navegador se abrirá en modo VISIBLE para debugging")
print()

captured_requests = []

def on_request(request):
    """Captura peticiones importantes (APIs, XHR, JSON)"""
    url = request.url
    method = request.method

    # Capturar APIs, endpoints REST, y peticiones JSON
    keywords = ['search', 'query', 'api', 'rest', 'json', 'xhr', 'graphql', 'results', 'document']

    # Solo capturar peticiones a Scopus (vía EZproxy o directo)
    if 'scopus' in url.lower() or '2057' in url or 'elsevier' in url.lower():
        if any(kw in url.lower() for kw in keywords):
            headers_dict = {}
            try:
                headers_dict = dict(request.headers)
            except:
                pass

            # Intentar capturar el body si es POST
            post_data = None
            try:
                if method == 'POST':
                    post_data = request.post_data
            except:
                pass

            captured_requests.append({
                'timestamp': time.time(),
                'method': method,
                'url': url,
                'headers': headers_dict,
                'post_data': post_data
            })

            # Mostrar en consola (truncado)
            url_short = url[:100] + '...' if len(url) > 100 else url
            print(f"📡 {method:6} {url_short}")

def on_response(response):
    """Captura respuestas importantes"""
    url = response.url

    # Solo respuestas de Scopus
    if 'scopus' in url.lower() or '2057' in url or 'elsevier' in url.lower():
        # Buscar respuestas JSON con resultados
        if 'search' in url.lower() or 'results' in url.lower() or 'document' in url.lower():
            try:
                content_type = response.headers.get('content-type', '')
                if 'json' in content_type.lower():
                    # Intentar parsear JSON
                    try:
                        data = response.json()
                        print(f"   ✅ JSON Response: {len(str(data))} bytes")

                        # Si tiene resultados, guardar aparte
                        if isinstance(data, dict):
                            if any(k in data for k in ['results', 'searchResults', 'documents', 'entries', 'items']):
                                print(f"   🎯 POSIBLE ENDPOINT DE BÚSQUEDA ENCONTRADO!")

                                # Guardar este endpoint especial
                                with open('scopus_search_endpoint.json', 'w', encoding='utf-8') as f:
                                    json.dump({
                                        'url': url,
                                        'method': response.request.method,
                                        'response_sample': str(data)[:500]  # Muestra
                                    }, f, indent=2, ensure_ascii=False)
                    except:
                        pass
            except:
                pass

try:
    print("⏳ Iniciando Playwright (navegador VISIBLE)...")
    print()

    with sync_playwright() as p:
        # Navegador VISIBLE para debugging
        browser = p.chromium.launch(
            headless=False,
            args=['--start-maximized']
        )

        context = browser.new_context(
            viewport=None,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()

        # Capturar peticiones y respuestas
        page.on("request", on_request)
        page.on("response", on_response)

        print("=" * 80)
        print("FASE 1: NAVEGACIÓN A SCOPUS VÍA EZPROXY")
        print("=" * 80)
        print()

        print("1️⃣  Navegando a Scopus vía bvirtual.epn.edu.ec...")
        print("   URL: https://bvirtual.epn.edu.ec:2057/pages/home?display=basic#basic")
        print()

        try:
            page.goto(
                'https://bvirtual.epn.edu.ec:2057/pages/home?display=basic#basic',
                wait_until='networkidle',
                timeout=60000
            )
        except Exception as e:
            print(f"⚠️  Timeout o error navegando: {e}")
            print("   Intentando con URL de login...")
            page.goto(
                'https://bvirtual.epn.edu.ec/login?url=http://www.scopus.com',
                wait_until='networkidle',
                timeout=60000
            )

        time.sleep(3)

        current_url = page.url
        title = page.title()

        print(f"   ✓ URL actual: {current_url}")
        print(f"   ✓ Título: {title}")
        print()

        # Verificar si llegamos a Scopus
        if "scopus" not in current_url.lower() and "2057" not in current_url:
            print("⚠️  No estamos en Scopus. Posibles causas:")
            print("   - Sesión expirada")
            print("   - No estás en la red de la EPN")
            print("   - EZproxy pidió login (verifica el navegador)")
            print()
            print("📸 Capturando screenshot...")
            page.screenshot(path='scopus_error.png')
            print("   Guardado: scopus_error.png")
            print()
            input("⏸️  Presiona Enter cuando estés en Scopus (después de loguearte manualmente si es necesario)...")

        print()
        print("=" * 80)
        print("FASE 2: BÚSQUEDA EN SCOPUS")
        print("=" * 80)
        print()

        print("2️⃣  Ejecutando búsqueda de prueba...")
        print("   Query: 'machine learning'")
        print()

        # Esperar a que cargue bien
        time.sleep(2)

        # Buscar campo de búsqueda (Scopus tiene varios selectores posibles)
        search_selectors = [
            'input[name="query"]',
            'input[id="queryField"]',
            'input[placeholder*="search" i]',
            'input[placeholder*="Enter" i]',
            'textarea[name="query"]',
            '#searchfield',
            '.searchField'
        ]

        search_box = None
        for selector in search_selectors:
            try:
                search_box = page.query_selector(selector)
                if search_box and search_box.is_visible():
                    print(f"   ✓ Campo de búsqueda encontrado: {selector}")
                    break
            except:
                continue

        if search_box:
            print("   ✓ Escribiendo query: 'machine learning'")
            search_box.fill('machine learning')
            time.sleep(1)

            print("   ✓ Presionando Enter...")
            search_box.press('Enter')

            print("   ⏳ Esperando resultados y capturando peticiones (10 segundos)...")
            print()
            time.sleep(10)

            result_url = page.url
            print(f"   ✓ URL de resultados: {result_url[:80]}...")
            print()

        else:
            print("   ✗ No se encontró campo de búsqueda automáticamente")
            print()
            print("=" * 80)
            print("MODO MANUAL")
            print("=" * 80)
            print()
            print("Por favor, ejecuta una búsqueda MANUALMENTE en el navegador:")
            print("  1. Busca 'machine learning'")
            print("  2. Presiona Enter")
            print("  3. Espera a que carguen los resultados")
            print()
            input("⏸️  Cuando termines, presiona Enter aquí para continuar...")
            print()
            print("⏳ Capturando peticiones adicionales (5 segundos)...")
            time.sleep(5)

        browser.close()

    # Análisis de peticiones capturadas
    print()
    print("=" * 80)
    print("PETICIONES CAPTURADAS")
    print("=" * 80)
    print()

    if not captured_requests:
        print("⚠️  No se capturaron peticiones de búsqueda")
        print()
        print("Posibles causas:")
        print("- No se ejecutó la búsqueda")
        print("- Scopus usa WebSockets (no HTTP)")
        print("- El sitio carga resultados desde HTML embebido")
        print()
        sys.exit(1)

    print(f"Total capturadas: {len(captured_requests)}\n")

    # Lista todas
    for i, req in enumerate(captured_requests, 1):
        method = req['method']
        url = req['url']
        print(f"{i:2}. {method:6} {url}")

    print()

    # Buscar endpoints de API REST
    api_endpoints = [
        r for r in captured_requests
        if 'api' in r['url'].lower() or
           'search' in r['url'].lower() or
           'results' in r['url'].lower() or
           'document' in r['url'].lower()
    ]

    if api_endpoints:
        print("=" * 80)
        print("🎯 ENDPOINTS CANDIDATOS (API/REST)")
        print("=" * 80)
        print()

        for endpoint in api_endpoints:
            print(f"🔗 {endpoint['method']} {endpoint['url']}")

            # Mostrar POST data si existe
            if endpoint.get('post_data'):
                print(f"   📦 POST Data: {endpoint['post_data'][:200]}...")

            # Headers importantes
            important_headers = ['content-type', 'authorization', 'cookie', 'x-api-key']
            headers = endpoint.get('headers', {})

            for h in important_headers:
                if h in [k.lower() for k in headers.keys()]:
                    value = headers.get(h, headers.get(h.title(), ''))
                    value_short = value[:50] + '...' if len(value) > 50 else value
                    print(f"   {h.title()}: {value_short}")

            print()

    # Guardar JSON
    with open('captured_scopus_requests.json', 'w', encoding='utf-8') as f:
        json.dump(captured_requests, f, indent=2, ensure_ascii=False)

    print("=" * 80)
    print("CONCLUSIÓN")
    print("=" * 80)
    print()
    print(f"✅ Peticiones guardadas: captured_scopus_requests.json")
    print(f"✅ Total capturadas: {len(captured_requests)}")
    print(f"✅ Endpoints candidatos: {len(api_endpoints)}")
    print()

    if Path('scopus_search_endpoint.json').exists():
        print("🎯 ¡ENDPOINT DE BÚSQUEDA IDENTIFICADO!")
        print("   Ver: scopus_search_endpoint.json")
        print()

    print("📋 SIGUIENTE PASO:")
    print("   1. Revisa captured_scopus_requests.json")
    print("   2. Busca endpoints que retornen JSON con resultados")
    print("   3. Copia la URL completa del endpoint")
    print("   4. Actualiza ScopusConnector._search_via_api() con esa URL")
    print()

except KeyboardInterrupt:
    print("\n⚠️  Interrumpido por usuario")
    sys.exit(0)

except Exception as e:
    print()
    print("=" * 80)
    print("❌ ERROR")
    print("=" * 80)
    print()
    print(f"Tipo: {type(e).__name__}")
    print(f"Mensaje: {e}")
    print()
    import traceback
    traceback.print_exc()
    sys.exit(1)
