"""
Test rápido de IEEE Connector.
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

from apps.acquisition.discovery.adapters.outbound.connectors.ieee_connector import IeeeConnector

load_dotenv()

username = os.getenv('EPN_USER')
password = os.getenv('EPN_PASS')

if not username or not password:
    print("❌ ERROR: EPN_USER/EPN_PASS no configurados")
    sys.exit(1)

TEST_QUERY = "machine learning"
MAX_RESULTS = 3

print("=" * 80)
print("TEST IEEE XPLORE")
print("=" * 80)
print()

try:
    print("⏳ Creando connector...")
    ieee = IeeeConnector(username, password, headless=True)
    print("✅ Connector creado")
    print()

    print(f"⏳ Buscando: '{TEST_QUERY}' (max: {MAX_RESULTS})...")
    print()

    results = list(ieee.search(TEST_QUERY, max_results=MAX_RESULTS))

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
    output_file = "ieee_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"💾 Guardado: {output_file}")
    print()

    # Análisis de campos
    print("📊 ANÁLISIS:")
    print(f"   Títulos:   {sum(1 for r in results if r.get('title'))}/{len(results)}")
    print(f"   DOI:       {sum(1 for r in results if r.get('doi'))}/{len(results)}")
    print(f"   Autores:   {sum(1 for r in results if r.get('authors'))}/{len(results)}")
    print(f"   Año:       {sum(1 for r in results if r.get('year'))}/{len(results)}")
    print(f"   Abstract:  {sum(1 for r in results if r.get('abstract'))}/{len(results)}")
    print()

    print("=" * 80)
    print("✅ TEST EXITOSO")
    print("=" * 80)

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
