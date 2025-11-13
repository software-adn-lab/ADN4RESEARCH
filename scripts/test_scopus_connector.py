"""
Script para probar ScopusConnector y descubrir endpoint de búsqueda.

Uso:
    python scripts/test_scopus_connector.py

NOTA: Este script ayuda a identificar el endpoint real de búsqueda de Scopus.
      Requiere estar en red EPN o VPN institucional.
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

from apps.acquisition.discovery.adapters.outbound.connectors.scopus_connector import ScopusConnector
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
print("TEST: Scopus Connector (Sesión Persistente)")
print("=" * 70)
print()
print(f"Usuario: {USERNAME}")
print("Query: 'machine learning'")
print("Max resultados: 10")
print()
print("⚠️  NOTA: Este conector requiere investigar el endpoint de Scopus.")
print("   Para descubrirlo:")
print("   1. Abre navegador en modo visible (headless=False)")
print("   2. Inspecciona Network en DevTools")
print("   3. Busca 'machine learning' manualmente")
print("   4. Identifica el XHR/Fetch que retorna JSON con resultados")
print()

try:
    # Crear conector
    connector = ScopusConnector(
        username=USERNAME,
        password=PASSWORD,
        headless=False,  # False = ver navegador
        rate_limit=2.0
    )

    print("🔍 Iniciando búsqueda...")
    print()

    # Intentar autenticación (esto abrirá el navegador)
    if connector.session_manager.ensure_authenticated():
        print("✅ Autenticación exitosa")
        print()
        print("🔧 ACCIÓN MANUAL REQUERIDA:")
        print("   1. Ve a la ventana del navegador que se abrió")
        print("   2. Busca 'machine learning' en Scopus manualmente")
        print("   3. Abre DevTools (F12) → Pestaña Network")
        print("   4. Filtra por XHR/Fetch")
        print("   5. Identifica el request que trae los resultados")
        print("   6. Copia la URL y estructura del payload")
        print("   7. Actualiza scopus_connector.py con esa info")
        print()
        print("Presiona Enter cuando termines de investigar...")
        input()

        # Intentar búsqueda (por ahora retornará vacío)
        results = list(connector.search('machine learning', max_results=10))

        print()
        print("=" * 70)
        print(f"RESULTADOS ({len(results)} estudios)")
        print("=" * 70)
        print()

        if results:
            for i, study in enumerate(results, 1):
                print(f"{i}. {study['title']}")
                print(f"   Autores: {', '.join(study.get('authors', [])[:3])}")
                print(f"   Año: {study.get('year', 'N/A')}")
                print(f"   DOI: {study.get('doi', 'N/A')}")
                print(f"   Link: {study['link']}")
                print()
        else:
            print("⚠️  No hay resultados (implementación pendiente)")
            print()

        print("SIGUIENTE PASO:")
        print("- Actualizar scopus_connector.py:_search_via_api() con endpoint real")
        print()
    else:
        print("❌ No se pudo autenticar")

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
