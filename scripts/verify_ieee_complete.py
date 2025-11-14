"""
Script de verificación COMPLETA del sistema IEEE.

Este script prueba:
1. Detección de red (acceso directo por IP vs autenticación)
2. Session Manager (cookies, autenticación)
3. Búsqueda vía API REST de IEEE
4. Extracción de datos (título, autores, abstract, etc.)
5. Validación de estructura de respuesta

Objetivo: Confirmar que el camino de extracción de datos es correcto.
"""
import sys
from pathlib import Path
import json
from dotenv import load_dotenv
import os

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Agregar el directorio raíz al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.acquisition.discovery.adapters.outbound.connectors.ieee_session_manager import (
    IeeeSessionManager
)
from apps.acquisition.discovery.adapters.outbound.connectors.ieee_connector import (
    IeeeConnector
)

# Cargar variables de entorno
load_dotenv()

print("=" * 80)
print("VERIFICACIÓN COMPLETA DEL SISTEMA IEEE")
print("=" * 80)
print()

# Configuración
TEST_QUERY = "machine learning"
MAX_RESULTS = 5

username = os.getenv('EPN_USER')
password = os.getenv('EPN_PASS')

if not username or not password:
    print("⚠️  ADVERTENCIA: EPN_USER o EPN_PASS no configurados en .env")
    print("   Funcionará solo si estás en la red de la universidad")
    print()
    username = "test"
    password = "test"

# ============================================================================
# TEST 1: SESSION MANAGER - DETECCIÓN DE RED
# ============================================================================

print("=" * 80)
print("TEST 1: DETECCIÓN DE RED Y SESSION MANAGER")
print("=" * 80)
print()

print("1️⃣  Inicializando IeeeSessionManager...")
session_mgr = IeeeSessionManager(username, password)
print("   ✅ Session manager creado")
print()

print("2️⃣  Probando detección de acceso directo por IP...")
print("   (Si estás en la red universitaria, debería detectar acceso directo)")
print()

try:
    # Este método internamente detecta si tiene acceso directo o necesita login
    session_mgr.ensure_authenticated()
    session = session_mgr.session
    print("   ✅ Autenticación completada")

    # Verificar si usó acceso directo o cookies
    cookies_file = Path("ieee_session.json")
    if cookies_file.exists():
        print("   📁 Archivo de cookies encontrado: ieee_session.json")
        with open(cookies_file, 'r') as f:
            cookies_data = json.load(f)
            print(f"      Cookies guardadas: {len(cookies_data)} cookies")
    else:
        print("   ℹ️  No hay cookies guardadas (probablemente acceso directo por IP)")

    print()

except Exception as e:
    print(f"   ❌ Error en autenticación: {e}")
    print()
    print("🛑 DETENER: No se puede continuar sin autenticación válida")
    sys.exit(1)

# ============================================================================
# TEST 2: BÚSQUEDA VÍA API
# ============================================================================

print("=" * 80)
print("TEST 2: BÚSQUEDA VÍA API REST DE IEEE")
print("=" * 80)
print()

print(f"3️⃣  Realizando búsqueda de prueba: '{TEST_QUERY}'")
print(f"   Límite de resultados: {MAX_RESULTS}")
print()

try:
    # Endpoint de búsqueda de IEEE (DIRECTO, no vía EZproxy)
    IEEE_SEARCH_API = "https://ieeexplore.ieee.org/rest/search"

    payload = {
        "queryText": TEST_QUERY,
        "highlight": True,
        "returnFacets": ["ALL"],
        "returnType": "SEARCH",
        "matchPubs": True,
        "rowsPerPage": str(MAX_RESULTS),
        "pageNumber": "1"
    }

    print("   📡 Haciendo POST request a IEEE API...")
    print(f"      URL: {IEEE_SEARCH_API}")
    print(f"      Payload: {json.dumps(payload, indent=6)}")
    print()

    response = session.post(
        IEEE_SEARCH_API,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30
    )

    print(f"   Status Code: {response.status_code}")
    print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
    print()

    if response.status_code != 200:
        print(f"   ❌ Error: Status code {response.status_code}")
        print(f"   Respuesta: {response.text[:500]}")
        print()
        print("🛑 DETENER: La API no retornó 200 OK")
        sys.exit(1)

    print("   ✅ Respuesta exitosa (200 OK)")
    print()

except Exception as e:
    print(f"   ❌ Error en búsqueda: {e}")
    print()
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# TEST 3: ANÁLISIS DE RESPUESTA JSON
# ============================================================================

print("=" * 80)
print("TEST 3: ANÁLISIS DE ESTRUCTURA DE RESPUESTA")
print("=" * 80)
print()

try:
    data = response.json()

    print("4️⃣  Analizando estructura JSON...")
    print()

    # Mostrar keys principales
    print("   📋 Keys principales del JSON:")
    for key in data.keys():
        value = data[key]
        value_type = type(value).__name__

        if isinstance(value, list):
            print(f"      • {key}: {value_type} (longitud: {len(value)})")
        elif isinstance(value, dict):
            print(f"      • {key}: {value_type} (keys: {len(value)})")
        else:
            print(f"      • {key}: {value_type} = {value}")

    print()

    # Buscar array de resultados
    print("   🔍 Buscando array de resultados...")

    results_key = None
    for key in ['records', 'articles', 'results', 'documents', 'entries']:
        if key in data and isinstance(data[key], list):
            results_key = key
            print(f"      ✅ Encontrado: '{results_key}' con {len(data[results_key])} elementos")
            break

    if not results_key:
        print("      ❌ No se encontró array de resultados con keys comunes")
        print("      Keys disponibles:", list(data.keys()))
        print()
        print("      Mostrando estructura completa (primeros 1000 chars):")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
        print()
        sys.exit(1)

    results = data[results_key]
    print()

    # Guardar respuesta completa para análisis
    with open('ieee_api_response.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("   💾 Respuesta completa guardada: ieee_api_response.json")
    print()

except json.JSONDecodeError as e:
    print(f"   ❌ Error: La respuesta no es JSON válido")
    print(f"      {e}")
    print()
    print(f"   Contenido de respuesta (primeros 500 chars):")
    print(response.text[:500])
    sys.exit(1)

except Exception as e:
    print(f"   ❌ Error analizando respuesta: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# TEST 4: EXTRACCIÓN DE CAMPOS
# ============================================================================

print("=" * 80)
print("TEST 4: EXTRACCIÓN DE CAMPOS DE RESULTADOS")
print("=" * 80)
print()

print(f"5️⃣  Extrayendo campos de {len(results)} resultados...")
print()

if len(results) == 0:
    print("   ⚠️  No se encontraron resultados para la búsqueda")
    print("      Esto puede ser normal si la query no tiene coincidencias")
    print()
    sys.exit(0)

# Analizar estructura del primer resultado
print("   📄 Estructura del PRIMER resultado:")
print()

first_result = results[0]
print(f"      Tipo: {type(first_result).__name__}")

if isinstance(first_result, dict):
    print(f"      Keys disponibles ({len(first_result)} total):")
    for key in sorted(first_result.keys())[:20]:  # Primeros 20
        value = first_result[key]
        value_preview = str(value)[:60] if value else "None"
        print(f"         • {key}: {value_preview}")

    if len(first_result.keys()) > 20:
        print(f"         ... y {len(first_result.keys()) - 20} keys más")

print()

# Intentar extraer campos comunes
print("   🎯 Extrayendo campos importantes...")
print()

# Campos esperados de IEEE
expected_fields = {
    'title': ['title', 'articleTitle', 'name'],
    'authors': ['authors', 'author', 'creators', 'authorList'],
    'abstract': ['abstract', 'abstractText', 'summary'],
    'doi': ['doi', 'DOI'],
    'publicationDate': ['publicationDate', 'pubDate', 'date', 'publicationYear'],
    'publicationTitle': ['publicationTitle', 'journalTitle', 'journal'],
    'url': ['htmlUrl', 'url', 'link', 'pdfUrl']
}

extracted_count = 0
missing_fields = []

for field_name, possible_keys in expected_fields.items():
    found = False
    for key in possible_keys:
        if key in first_result:
            value = first_result[key]
            value_preview = str(value)[:80] if value else "None"
            print(f"      ✅ {field_name}: {value_preview}")
            found = True
            extracted_count += 1
            break

    if not found:
        print(f"      ❌ {field_name}: NO ENCONTRADO")
        missing_fields.append(field_name)

print()
print(f"   📊 Estadísticas:")
print(f"      ✅ Campos encontrados: {extracted_count}/{len(expected_fields)}")
print(f"      ❌ Campos faltantes: {len(missing_fields)}")

if missing_fields:
    print(f"         Faltantes: {', '.join(missing_fields)}")

print()

# ============================================================================
# TEST 5: INTEGRACIÓN CON CONNECTOR
# ============================================================================

print("=" * 80)
print("TEST 5: INTEGRACIÓN CON IeeeConnector")
print("=" * 80)
print()

print("6️⃣  Probando IeeeConnector completo...")
print()

try:
    connector = IeeeConnector(username, password)

    print(f"   📡 Ejecutando búsqueda: '{TEST_QUERY}'")
    articles = list(connector.search(TEST_QUERY, max_results=MAX_RESULTS))  # Convertir generator a lista

    print(f"   ✅ Búsqueda completada")
    print(f"   📊 Resultados obtenidos: {len(articles)}")
    print()

    if len(articles) > 0:
        print("   📄 PRIMER RESULTADO NORMALIZADO:")
        print()

        first_article = articles[0]
        for key, value in first_article.items():
            value_preview = str(value)[:100] if value else "None"
            print(f"      • {key}: {value_preview}")

        print()

        # Guardar resultados normalizados
        with open('ieee_normalized_results.json', 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)

        print("   💾 Resultados normalizados guardados: ieee_normalized_results.json")
        print()

except Exception as e:
    print(f"   ❌ Error en IeeeConnector: {e}")
    import traceback
    traceback.print_exc()
    print()
    sys.exit(1)

# ============================================================================
# RESUMEN FINAL
# ============================================================================

print("=" * 80)
print("✅ VERIFICACIÓN COMPLETADA EXITOSAMENTE")
print("=" * 80)
print()

print("📋 RESUMEN:")
print()
print(f"   ✅ Session Manager: Funcionando")
print(f"   ✅ API REST de IEEE: Funcionando")
print(f"   ✅ Respuesta JSON: Válida")
print(f"   ✅ Extracción de campos: {extracted_count}/{len(expected_fields)} campos")
print(f"   ✅ IeeeConnector: Funcionando")
print(f"   ✅ Resultados obtenidos: {len(articles)}")
print()

print("📁 ARCHIVOS GENERADOS:")
print()
print("   • ieee_api_response.json - Respuesta cruda de la API")
print("   • ieee_normalized_results.json - Resultados normalizados")
if cookies_file.exists():
    print("   • ieee_session.json - Cookies de sesión")
print()

print("=" * 80)
print("🎯 SIGUIENTE PASO:")
print("=" * 80)
print()

if missing_fields:
    print("⚠️  HAY CAMPOS FALTANTES:")
    print()
    print(f"   Campos no encontrados: {', '.join(missing_fields)}")
    print()
    print("   ACCIÓN REQUERIDA:")
    print("   1. Revisa ieee_api_response.json para ver la estructura real")
    print("   2. Identifica los nombres correctos de los campos faltantes")
    print("   3. Actualiza IeeeConnector._search_via_api() con los nombres correctos")
    print()
else:
    print("✅ TODOS LOS CAMPOS FUERON ENCONTRADOS")
    print()
    print("   El sistema IEEE está COMPLETAMENTE FUNCIONAL")
    print("   Puedes proceder a:")
    print()
    print("   1. Implementar Scopus usando el mismo patrón")
    print("   2. Integrar con el sistema de búsqueda principal")
    print("   3. Agregar más fuentes de datos")
    print()

print("=" * 80)
