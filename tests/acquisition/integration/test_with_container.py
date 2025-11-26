"""
Test simplificado usando Container directamente.

Este test demuestra cómo los tests DEBERÍAN usar el Container
en lugar de construir servicios manualmente.

VENTAJAS:
1. Tests más simples y mantenibles
2. Usa la misma configuración que producción
3. No duplica lógica de construcción
4. Respeta Dependency Injection

Ejecutar:
    python scripts/test_with_container.py
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Fix encoding Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv()

# Configurar Django ANTES de importar modelos
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.acquisition.container import Container
from apps.acquisition.models import SearchStrategyModel, SearchExecutionModel, StudyModel, ExecutionStudy

print("=" * 80)
print("TEST USANDO CONTAINER DIRECTAMENTE")
print("=" * 80)
print()

# ============================================================================
# CONFIGURACIÓN DEL TEST
# ============================================================================

strategy_dict = {
    "strategy_id": "test_container_2024",
    "main_terms": [
        {
            "term": "artificial intelligence",
            "synonyms": ["AI", "machine learning"]
        }
    ],
    "exclusions": ["robotics"],
    "filters": {}
}

print("📋 Estrategia de búsqueda:")
print(f"  ID: {strategy_dict['strategy_id']}")
print(f"  Términos: {strategy_dict['main_terms'][0]['term']}")
print(f"  Sinónimos: {strategy_dict['main_terms'][0]['synonyms']}")
print()

# ============================================================================
# EJECUTAR PIPELINE COMPLETO USANDO ORCHESTRATOR
# ============================================================================

print("🚀 Ejecutando pipeline completo con Orchestrator...")
print()

# ✅ FORMA CORRECTA: Usar Container
orchestrator = Container.get_orchestrator()

try:
    result = orchestrator.execute_search_from_strategy(
        strategy_dict=strategy_dict
    )

    print("✅ Pipeline completado exitosamente")
    print()

    # ============================================================================
    # VERIFICAR PERSISTENCIA EN POSTGRESQL
    # ============================================================================

    print("=" * 80)
    print("VERIFICACIÓN DE PERSISTENCIA EN POSTGRESQL")
    print("=" * 80)
    print()

    # 1. Verificar SearchStrategyModel
    strategy_model = SearchStrategyModel.objects.get(id=result.strategy_id)
    print(f"✓ Estrategia guardada:")
    print(f"  ID: {strategy_model.id}")
    print(f"  Name: {strategy_model.name}")
    print(f"  Terms: {strategy_model.definition.get('main_terms', [])[:1]}")  # Mostrar primer término
    print()

    # 2. Verificar SearchExecutionModel
    execution_model = SearchExecutionModel.objects.get(id=result.execution_id)
    print(f"✓ Ejecución guardada:")
    print(f"  ID: {execution_model.id}")
    print(f"  Estado: {execution_model.status}")
    print(f"  Fuentes traducidas: {list(execution_model.translated_queries.keys())}")
    print()

    # 3. Verificar StudyModel
    studies = StudyModel.objects.filter(
        executionstudy__execution_id=result.execution_id
    )
    print(f"✓ Estudios guardados: {studies.count()}")
    for i, study in enumerate(studies[:3], 1):
        print(f"  {i}. {study.title[:60]}...")
        print(f"     Source: {study.source}, DOI: {study.doi or 'N/A'}")
    print()

    # 4. Verificar ExecutionStudy (M2M)
    links = ExecutionStudy.objects.filter(execution_id=result.execution_id)
    print(f"✓ Relaciones M2M guardadas: {links.count()}")
    for i, link in enumerate(links[:3], 1):
        print(f"  {i}. Study {link.study_id} → Execution {link.execution_id}")
        print(f"     Providers: {link.providers}, Is new: {link.is_new}")
    print()

    # ============================================================================
    # RESUMEN FINAL
    # ============================================================================

    print("=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print()

    print("✅ TRAZABILIDAD COMPLETA FUNCIONANDO:")
    print(f"  1. SearchStrategyModel  ✓ (ID: {strategy_model.id})")
    print(f"  2. SearchExecutionModel ✓ (ID: {execution_model.id})")
    print(f"  3. StudyModel           ✓ ({studies.count()} estudios)")
    print(f"  4. ExecutionStudy       ✓ ({links.count()} relaciones)")
    print()

    print("🎯 VENTAJAS DE USAR CONTAINER:")
    print("  ✓ Test más simple (1 línea vs 20+)")
    print("  ✓ Usa configuración de producción (.env)")
    print("  ✓ Repository inyectado automáticamente")
    print("  ✓ Connectors configurados automáticamente")
    print("  ✓ Más fácil de mantener")
    print()

    print("📍 CONFIGURACIÓN ACTUAL:")
    db_config = django.conf.settings.DATABASES['default']
    print(f"  DB Host: {db_config.get('HOST', 'localhost')}")
    print(f"  DB Name: {db_config.get('NAME', 'sqlite')}")
    print(f"  Storage: {'MinIO (S3)' if django.conf.settings.USE_S3 else 'Local filesystem'}")
    if not django.conf.settings.USE_S3:
        print(f"  Media Dir: {django.conf.settings.MEDIA_ROOT}")
    else:
        print(f"  S3 Endpoint: {django.conf.settings.AWS_S3_ENDPOINT_URL}")
    print()

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("=" * 80)
print("FIN DEL TEST")
print("=" * 80)
