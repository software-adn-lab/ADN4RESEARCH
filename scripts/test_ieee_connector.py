"""
Script para probar IeeePlaywrightConnector

Uso:
    python scripts/test_ieee_connector.py
"""
import sys
import os
from pathlib import Path

# Agregar el proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from apps.acquisition.discovery.adapters.outbound.connectors.ieee_connector import IeeeConnector
from dotenv import load_dotenv

# Cargar credenciales
load_dotenv()

USERNAME = os.getenv('EPN_USER')
PASSWORD = os.getenv('EPN_PASS')

if not USERNAME or not PASSWORD:
    print("❌ Error: Define EPN_USER y EPN_PASS en .env")
    print()
    print("Ejemplo .env:")
    print("EPN_USER=tu.correo@epn.edu.ec")
    print("EPN_PASS=tu_contraseña")
    sys.exit(1)

print("=" * 70)
print("TEST: IEEE Xplore Connector (Sesión Persistente)")
print("=" * 70)
print()
print(f"Usuario: {USERNAME}")
print("Query: 'machine learning'")
print("Max resultados: 10")
print()
print("NOTA: Si es la primera vez, abrirá navegador para autenticar.")
print("      Búsquedas subsecuentes usarán cookies guardadas (sin browser).")
print()

try:
    # Crear conector con sesión persistente
    connector = IeeeConnector(
        username=USERNAME,
        password=PASSWORD,
        headless=False,  # False = ver navegador durante autenticación
        rate_limit=2.0
    )

    print("🔍 Iniciando búsqueda...")
    print()

    results = list(connector.search('machine learning', max_results=10))

    print()
    print("=" * 70)
    print(f"RESULTADOS ({len(results)} estudios)")
    print("=" * 70)
    print()

    for i, study in enumerate(results, 1):
        print(f"{i}. {study['title']}")
        print(f"   Autores: {', '.join(study.get('authors', [])[:3])}")
        print(f"   Año: {study.get('year', 'N/A')}")
        print(f"   DOI: {study.get('doi', 'N/A')}")
        print(f"   Link: {study['link']}")
        print()

    print("✅ Test exitoso")
    print()
    print("NOTA: Las cookies se guardaron en .sessions/ieee_session.json")
    print("      La próxima búsqueda NO abrirá navegador (usará cookies).")
    print()

    # Cerrar conector
    connector.close()

except KeyboardInterrupt:
    print("\n⚠️  Interrumpido por usuario")
    sys.exit(0)

except Exception as e:
    print(f"❌ Error: {type(e).__name__}")
    print(f"   {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
