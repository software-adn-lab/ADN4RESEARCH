"""
Test de ScopusConnector con API oficial de Elsevier.

Prueba el flujo:
1. API oficial de Elsevier (rápido, con API key)
2. Fallback a Playwright si falla
"""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Fix encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.acquisition.discovery.adapters.outbound.connectors.scopus_connector import ScopusConnector

load_dotenv()

# Credenciales
username = os.getenv('EPN_USER')
password = os.getenv('EPN_PASS')
api_key = os.getenv('SCOPUS_API_KEY')  # API key de Elsevier

TEST_QUERY = "machine learning"
MAX_RESULTS = 5

print("=" * 80)
print("TEST SCOPUS CONNECTOR (API + FALLBACK)")
print("=" * 80)
print()

# Mostrar configuración
print("CONFIGURACIÓN:")
print(f"   API Key: {'✅ Configurada' if api_key else '❌ No configurada'}")
print(f"   EZproxy: {'✅ Configurado' if (username and password) else '❌ No configurado'}")
print()

if not api_key and not (username and password):
    print("❌ ERROR: Necesita SCOPUS_API_KEY o EPN_USER/EPN_PASS")
    print()
    print("Opciones:")
    print("   1. Obtener API key de Elsevier: https://dev.elsevier.com/")
    print("   2. Configurar credenciales EPN para fallback")
    sys.exit(1)

try:
    print("⏳ Creando ScopusConnector...")

    # El conector usará API si hay key, fallback si hay credenciales
    scopus = ScopusConnector(
        username=username,
        password=password,
        api_key=api_key,
        headless=True  # Para fallback
    )

    print("✅ Connector creado")
    print()

    print(f"⏳ Buscando: '{TEST_QUERY}' (max: {MAX_RESULTS})...")
    print()

    results = list(scopus.search(TEST_QUERY, max_results=MAX_RESULTS))

    print()
    print("=" * 80)
    print("RESULTADOS")
    print("=" * 80)
    print()

    if not results:
        print("⚠️  No se encontraron resultados")
        sys.exit(0)

    print(f"✅ Obtenidos {len(results)} resultados")
    print()

    # Mostrar primer resultado
    print("📄 PRIMER RESULTADO:")
    print()
    first = results[0]
    for key, value in first.items():
        if isinstance(value, list):
            value_str = ", ".join(str(v) for v in value[:3])
            if len(value) > 3:
                value_str += f" ... (+{len(value)-3} más)"
        elif isinstance(value, str) and len(value) > 100:
            value_str = value[:100] + "..."
        else:
            value_str = str(value)

        print(f"   • {key}: {value_str}")

    print()

    # Guardar
    output_file = "scopus_api_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"💾 Guardado: {output_file}")
    print()

    # Análisis de campos
    print("📊 ANÁLISIS DE COMPLETITUD:")
    print(f"   Títulos:     {sum(1 for r in results if r.get('title'))}/{len(results)}")
    print(f"   DOI:         {sum(1 for r in results if r.get('doi'))}/{len(results)}")
    print(f"   Autores:     {sum(1 for r in results if r.get('authors'))}/{len(results)}")
    print(f"   Año:         {sum(1 for r in results if r.get('year'))}/{len(results)}")
    print(f"   Abstract:    {sum(1 for r in results if r.get('abstract'))}/{len(results)}")
    print(f"   Link:        {sum(1 for r in results if r.get('link'))}/{len(results)}")
    print(f"   Cited by:    {sum(1 for r in results if r.get('cited_by'))}/{len(results)}")
    print()

    print("=" * 80)
    print("✅ TEST EXITOSO")
    print("=" * 80)

    # Cerrar conector
    scopus.close()

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
