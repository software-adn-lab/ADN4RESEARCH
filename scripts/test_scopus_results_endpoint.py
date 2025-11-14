"""
Script para probar el endpoint de resultados de Scopus y determinar cómo extraer datos.

Este script:
1. Autentica en Scopus vía EZproxy (si es necesario)
2. Hace request a /results/results.uri con parámetros de búsqueda
3. Analiza la respuesta (HTML, JSON, otro formato)
4. Identifica qué enfoque usar (API, HTML parsing, etc.)
"""
import requests
from bs4 import BeautifulSoup
import json
import sys
from pathlib import Path

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Agregar el directorio raíz al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.acquisition.discovery.adapters.outbound.connectors.scopus_session_manager import (
    ScopusSessionManager
)
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

print("=" * 80)
print("TEST: SCOPUS RESULTS ENDPOINT")
print("=" * 80)
print()

# URL base de Scopus vía EZproxy
SCOPUS_BASE = "https://bvirtual.epn.edu.ec:2057"
# SCOPUS_BASE = "https://www.scopus.com"  # Probar también sin EZproxy

print("1️⃣  Inicializando session manager...")
username = os.getenv('EPN_USER')
password = os.getenv('EPN_PASS')

if not username or not password:
    print("   ⚠️  EPN_USER o EPN_PASS no configurados en .env")
    print("   Usando valores de prueba...")
    username = "test"
    password = "test"

session_mgr = ScopusSessionManager(username, password)

try:
    print("2️⃣  Autenticando (si es necesario)...")
    session_mgr.ensure_authenticated()
    session = session_mgr.session  # La sesión real está aquí
    print("   ✅ Sesión lista")
    print()

    # Construir URL de búsqueda (basada en la captura)
    search_query = "machine learning"
    search_params = {
        "st1": search_query,
        "st2": "",
        "loadDate": "",
        "s": f"TITLE-ABS-KEY({search_query})",
        "limit": "10",
        "origin": "searchbasic",
        "sort": "plf-f",  # publication date, newest first
        "src": "s",
        "sot": "b",
        "sdt": "b"
    }

    results_url = f"{SCOPUS_BASE}/results/results.uri"

    print("3️⃣  Haciendo request a endpoint de resultados...")
    print(f"   URL: {results_url}")
    print(f"   Params: {search_params}")
    print()

    response = session.get(
        results_url,
        params=search_params,
        timeout=30
    )

    print(f"   Status Code: {response.status_code}")
    print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
    print(f"   Content Length: {len(response.content)} bytes")
    print()

    # Guardar respuesta para análisis
    response_file = "scopus_results_response.html"
    with open(response_file, 'wb') as f:
        f.write(response.content)
    print(f"   ✅ Respuesta guardada: {response_file}")
    print()

    # Analizar contenido
    content_type = response.headers.get('content-type', '').lower()

    if 'json' in content_type:
        print("=" * 80)
        print("🎯 RESPUESTA ES JSON!")
        print("=" * 80)
        print()
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
        print()
        print("💡 SIGUIENTE PASO:")
        print("   ✅ Scopus tiene API JSON")
        print("   ✅ Implementar ScopusConnector._search_via_api() con este endpoint")
        print()

    elif 'html' in content_type:
        print("=" * 80)
        print("⚠️  RESPUESTA ES HTML")
        print("=" * 80)
        print()

        # Parsear HTML con BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Buscar posibles estructuras de datos embebidos
        print("4️⃣  Analizando HTML...")
        print()

        # Opción A: JSON embebido en <script>
        script_tags = soup.find_all('script', type='application/json')
        if script_tags:
            print(f"   ✅ Encontrados {len(script_tags)} tags <script type='application/json'>")
            for i, tag in enumerate(script_tags[:3], 1):
                print(f"      {i}. {tag.get('id', 'No ID')} - {len(tag.string)} chars")
                if tag.string:
                    try:
                        data = json.loads(tag.string)
                        print(f"         JSON válido con keys: {list(data.keys())[:5]}")
                    except:
                        pass
            print()

        # Opción B: Window.__INITIAL_STATE__ o similar
        all_scripts = soup.find_all('script')
        for script in all_scripts[:20]:  # Primeros 20
            if script.string and ('__INITIAL' in script.string or 'window.' in script.string or 'SCOPUS' in script.string):
                lines = script.string.strip().split('\n')
                for line in lines[:5]:
                    if '__INITIAL' in line or 'SCOPUS' in line or 'results' in line.lower():
                        print(f"   🔍 Encontrado en <script>: {line[:100]}")

        print()

        # Opción C: Elementos HTML con resultados
        # Buscar divs/articles que puedan ser resultados
        possible_results = soup.find_all(['div', 'article'], class_=lambda x: x and ('result' in x.lower() or 'document' in x.lower() or 'item' in x.lower()))

        if possible_results:
            print(f"   📄 Encontrados {len(possible_results)} elementos HTML que parecen resultados")
            first_result = possible_results[0]
            print(f"      Clases del primero: {first_result.get('class', [])}")
            print(f"      ID del primero: {first_result.get('id', 'No ID')}")

            # Intentar extraer título del primero
            title_elem = first_result.find(['h2', 'h3', 'h4', 'a'], class_=lambda x: x and 'title' in x.lower())
            if title_elem:
                print(f"      Título encontrado: {title_elem.get_text()[:80]}...")
        else:
            print("   ⚠️  No se encontraron elementos HTML obvios con resultados")

        print()
        print("=" * 80)
        print("💡 SIGUIENTE PASO:")
        print("=" * 80)
        print()
        print("   OPCIÓN A: Si hay JSON embebido en <script>:")
        print("      → Extraer JSON del HTML y parsearlo")
        print("      → Más confiable que parsear HTML puro")
        print()
        print("   OPCIÓN B: Si NO hay JSON embebido:")
        print("      → Web scraping con BeautifulSoup")
        print("      → Parsear elementos HTML (más frágil)")
        print()
        print(f"   📄 Revisa el archivo {response_file} para más detalles")
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
