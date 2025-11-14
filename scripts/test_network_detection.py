"""
Script para verificar detección automática de red (IP vs Login).

Este script muestra cómo el sistema detecta automáticamente si estás
en la red universitaria o fuera de ella.

Uso:
    python scripts/test_network_detection.py
"""
import sys
import os
from pathlib import Path
import logging

# Agregar el proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from apps.acquisition.discovery.adapters.outbound.connectors.ieee_connector import IeeeConnector
from dotenv import load_dotenv

# Configurar logging para ver el proceso
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

# Cargar credenciales
load_dotenv()

USERNAME = os.getenv('EPN_USER')
PASSWORD = os.getenv('EPN_PASS')

if not USERNAME or not PASSWORD:
    print("=" * 80)
    print("⚠️  ADVERTENCIA: No hay credenciales configuradas")
    print("=" * 80)
    print()
    print("Las credenciales solo son necesarias si estás FUERA de la red EPN.")
    print()
    print("Si estás EN LA RED universitaria:")
    print("  → El sistema detectará acceso por IP y NO pedirá credenciales")
    print()
    print("Si estás FUERA de la red:")
    print("  → Configura credenciales en .env:")
    print("    EPN_USER=tu.correo@epn.edu.ec")
    print("    EPN_PASS=tu_contraseña")
    print()
    print("Continuando con test de detección de red (sin credenciales)...")
    print()
    USERNAME = "dummy@epn.edu.ec"
    PASSWORD = "dummy"

print("=" * 80)
print("🔍 TEST: Detección Automática de Red")
print("=" * 80)
print()
print("Este test verifica si estás EN LA RED o FUERA de la red EPN.")
print()
print("ESCENARIOS:")
print("  1. EN LA RED: Acceso directo por IP → Sin login → Sin cookies → RÁPIDO")
print("  2. FUERA: Login automático con Playwright → Guarda cookies")
print()
print("=" * 80)
print()

try:
    # Crear conector
    print("📡 Iniciando IEEE Connector...")
    print()

    connector = IeeeConnector(
        username=USERNAME,
        password=PASSWORD,
        headless=True,
        rate_limit=1.0
    )

    print()
    print("🔍 Ejecutando búsqueda de prueba...")
    print("   Query: 'machine learning'")
    print("   Max resultados: 3")
    print()
    print("-" * 80)

    # Ejecutar búsqueda (esto activará la detección de red)
    results = list(connector.search('machine learning', max_results=3))

    print("-" * 80)
    print()

    # Mostrar resultados
    print("=" * 80)
    print(f"✅ BÚSQUEDA EXITOSA ({len(results)} resultados)")
    print("=" * 80)
    print()

    for i, study in enumerate(results, 1):
        print(f"{i}. {study['title']}")
        authors = study.get('authors', [])
        if authors:
            print(f"   Autores: {', '.join(authors[:3])}")
        print(f"   Año: {study.get('year', 'N/A')}")
        print(f"   DOI: {study.get('doi', 'N/A')}")
        print(f"   Link: {study['link'][:80]}...")
        print()

    print("=" * 80)
    print("📊 RESUMEN")
    print("=" * 80)
    print()

    # Verificar si hay cookies guardadas
    session_file = Path(".sessions/ieee_session.json")
    if session_file.exists():
        print("📁 Sesión guardada: .sessions/ieee_session.json")
        print("   → Las cookies se reutilizarán en próximas búsquedas")
        print("   → No se abrirá navegador de nuevo")
    else:
        print("📁 No hay sesión guardada")
        print("   → Probablemente accediste por IP (red universitaria)")
        print("   → No se necesitan cookies")

    print()
    print("✅ Test completado exitosamente")
    print()

    # Cerrar conector
    connector.close()

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

    # Diagnóstico
    print("🔍 DIAGNÓSTICO:")
    print()

    if "No se pudo autenticar" in str(e):
        print("⚠️  El sistema intentó autenticarse pero falló.")
        print()
        print("Posibles causas:")
        print("  1. Estás FUERA de la red y las credenciales son incorrectas")
        print("  2. El portal EZproxy cambió su interfaz de login")
        print("  3. Problema de conexión a internet")
        print()
        print("Soluciones:")
        print("  - Verifica credenciales en .env (EPN_USER, EPN_PASS)")
        print("  - Intenta desde la red universitaria (no necesita credenciales)")
        print("  - Verifica tu conexión a internet")

    elif "Connection" in str(e) or "Timeout" in str(e):
        print("⚠️  Problema de conexión.")
        print()
        print("Verifica:")
        print("  - Conexión a internet activa")
        print("  - Firewall no bloquea Python/Playwright")

    else:
        print("Error inesperado. Traceback completo:")
        print()
        import traceback
        traceback.print_exc()

    print()
    sys.exit(1)
