"""
Test directo de descarga desde Sci-Hub para diagnóstico.
"""
import sys
import os
sys.path.append(os.getcwd())

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from apps.acquisition.downloads.adapters.outbound.connectors.scihub_downloader import SciHubDownloader
from apps.acquisition.downloads.adapters.outbound.storage.django_storage import DjangoStorage

print("=" * 80)
print("TEST DIRECTO DE SCI-HUB")
print("=" * 80)

# DOI de prueba (paper IEEE que debería estar en Sci-Hub)
test_doi = "10.1109/ICSE-SEET52601.2021.00012"

print(f"\n📄 DOI de prueba: {test_doi}")
print(f"   Paper: Teaching the Scrum Master Role...")

# Inicializar Sci-Hub con storage real
storage = DjangoStorage()
scihub = SciHubDownloader(
    storage=storage,
    enabled=True,
    timeout=30,
    delay_range=(1.0, 2.0),  # Delays más cortos para testing
    use_cache=False  # Sin caché para testing limpio
)

print("\n🌐 Dominios de Sci-Hub configurados:")
for i, domain in enumerate(scihub.SCIHUB_DOMAINS, 1):
    print(f"   {i}. {domain}")

print("\n📥 Intentando descarga...")
print("-" * 80)

result = scihub.download(test_doi)

print("-" * 80)
print("\n📊 RESULTADO:")
if result:
    print(f"   ✅ PDF descargado exitosamente")
    print(f"   📍 Ruta en storage: {result}")
    
    # Verificar en storage
    if storage.exists(result):
        size = storage.size(result)
        print(f"   📦 Tamaño: {size:,} bytes ({size/1024:.1f} KB)")
        print(f"\n💡 Verifica en MinIO Console:")
        print(f"   http://localhost:9001")
        print(f"   Buscar: {result}")
    else:
        print(f"   ⚠️  Archivo no encontrado en storage (inconsistencia)")
else:
    print(f"   ❌ No se pudo descargar el PDF")
    print(f"\n🔍 Posibles causas:")
    print(f"   1. Sci-Hub no tiene este paper")
    print(f"   2. Sci-Hub bloqueó la IP (rate limiting)")
    print(f"   3. Problemas de red/timeout")
    print(f"   4. Paper protegido por paywall fuerte")
    
    print(f"\n💡 Intenta:")
    print(f"   1. Verificar manualmente: https://sci-hub.se/{test_doi}")
    print(f"   2. Probar con otro DOI conocido en Sci-Hub")
    print(f"   3. Revisar logs arriba para ver qué dominio falló")

print("\n" + "=" * 80)