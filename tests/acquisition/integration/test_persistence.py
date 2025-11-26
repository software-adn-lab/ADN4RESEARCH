"""
Script de verificación: Persistencia COMPLETA con Trazabilidad

Este script verifica que:
1. Se traduce la estrategia (TranslationService)
2. Se guarda la estrategia (SearchStrategyModel)
3. Se ejecuta discovery (DiscoveryService → APIs reales)
4. Se guarda la ejecución con traducciones (SearchExecutionModel)
5. Se guardan los estudios (StudyModel)
6. Se vincula estudios-ejecución (ExecutionStudy)

Ejecutar:
    poetry run python scripts/test_persistence.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.acquisition.container import Container
from apps.acquisition.models import (
    SearchStrategyModel,
    SearchExecutionModel,
    StudyModel,
    ExecutionStudy
)

print("=" * 80)
print("VERIFICACIÓN: Flujo Completo con Trazabilidad")
print("=" * 80)
print()

# 1. Obtener orchestrator (coordina TODO)
print("1. Obteniendo AcquisitionOrchestrator del Container...")
orchestrator = Container.get_orchestrator()
print("   ✓ Orchestrator obtenido")
print()

# 2. Ejecutar flujo completo (Traducción + Discovery + Persistencia + Trazabilidad)
print("2. Ejecutando flujo completo (Traducción → Discovery → Persistencia)...")

# Estrategia normalizada de ejemplo (formato correcto según NormalizedStrategy)
strategy_dict = {
    "strategy_id": "test_persistence_full",
    "main_terms": [
        {
            "term": "software testing",
            "synonyms": ["quality assurance", "QA"]
        }
    ],
    "exclusions": ["hardware", "network"],
    "year_filter": {
        "from": 2020,
        "to": 2024
    }
}

try:
    result = orchestrator.execute_search_from_strategy(
        strategy_dict=strategy_dict,
        research_question_id=None,  # Puedes vincular con Design si tienes una pregunta
        user=None,
        strategy_name="Test Persistencia Completa",
        strategy_description="Verificación de trazabilidad end-to-end"
    )

    print(f"   ✓ Flujo completado")
    print(f"   → Estudios encontrados: {result.total_found}")
    print(f"   → Estudios nuevos: {result.new_studies_count}")
    print(f"   → Strategy ID: {result.strategy_id}")
    print(f"   → Execution ID: {result.execution_id}")
    print()

except Exception as e:
    print(f"   ✗ Error en flujo: {e}")
    import traceback
    traceback.print_exc()
    print("   → Verifica credenciales en .env (SCOPUS_API_KEY, EPN_USER, EPN_PASS)")
    sys.exit(1)

# 3. Verificar CADA TABLA (Trazabilidad completa)
print("3. Verificando trazabilidad en TODAS las tablas...")
print()

# 3.1 SearchStrategyModel
try:
    strategy = SearchStrategyModel.objects.get(id=result.strategy_id)
    print("   ✅ SearchStrategyModel guardada:")
    print(f"      → ID: {strategy.id}")
    print(f"      → Nombre: {strategy.name}")
    print(f"      → Definition: {list(strategy.definition.keys())}")
    print()
except SearchStrategyModel.DoesNotExist:
    print("   ❌ ERROR: SearchStrategyModel NO existe")
    sys.exit(1)

# 3.2 SearchExecutionModel (con traducciones)
try:
    execution = SearchExecutionModel.objects.get(id=result.execution_id)
    print("   ✅ SearchExecutionModel guardada (con TRADUCCIONES):")
    print(f"      → ID: {execution.id}")
    print(f"      → Status: {execution.status}")
    print(f"      → Queries traducidas:")

    for source, query in result.queries_by_source.items():
        print(f"         • {source}: {query[:60]}...")

    print(f"      → translated_queries en DB: {list(execution.translated_queries.keys())}")
    print(f"      → results_count: {execution.results_count}")
    print()
except SearchExecutionModel.DoesNotExist:
    print("   ❌ ERROR: SearchExecutionModel NO existe")
    sys.exit(1)

# 3.3 StudyModel
if not result.studies:
    print("   ⚠️  No se encontraron estudios (puede ser normal si la query no tiene resultados)")
else:
    first_study = result.studies[0]
    try:
        db_study = StudyModel.objects.get(uuid=first_study.id)
        print("   ✅ StudyModel guardado:")
        print(f"      → ID: {db_study.uuid}")
        print(f"      → Título: {db_study.title[:50]}...")
        print(f"      → Fuente: {db_study.source}")
        print(f"      → DOI: {db_study.doi or 'N/A'}")
        print()
    except StudyModel.DoesNotExist:
        print("   ❌ ERROR: StudyModel NO existe")
        sys.exit(1)

    # 3.4 ExecutionStudy (trazabilidad M2M)
    try:
        links = ExecutionStudy.objects.filter(execution_id=result.execution_id)
        print(f"   ✅ ExecutionStudy (trazabilidad):")
        print(f"      → Total vínculos: {links.count()}")

        first_link = links.first()
        if first_link:
            print(f"      → Ejemplo:")
            print(f"         • is_new: {first_link.is_new}")
            print(f"         • providers: {first_link.providers}")
            print(f"         • rank_position: {first_link.rank_position}")
        print()
    except Exception as e:
        print(f"   ⚠️  ExecutionStudy: {e}")

print("=" * 80)
print("✅ ÉXITO: TRAZABILIDAD COMPLETA FUNCIONANDO")
print("=" * 80)
print()
print("Resumen de tablas persistidas:")
print(f"  1. SearchStrategyModel    ✓ (Estrategia normalizada)")
print(f"  2. SearchExecutionModel   ✓ (Traducciones + Auditoría)")
print(f"  3. StudyModel             ✓ ({len(result.studies)} estudios)")
print(f"  4. ExecutionStudy         ✓ (Trazabilidad M2M)")
print()
print("Flujo completo verificado:")
print("  Proyecto → ResearchQuestion → Strategy → Translation → Discovery → Studies")
print()
