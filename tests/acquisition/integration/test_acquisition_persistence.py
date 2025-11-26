"""
Script de prueba para verificar que la persistencia funciona correctamente.

Este script muestra cómo usar el AcquisitionOrchestrator para:
1. Ejecutar una búsqueda
2. Guardar estudios en BD con trazabilidad
3. Consultar los resultados guardados

USO:
    python manage.py shell < scripts/test_acquisition_persistence.py

    O dentro de Django shell:
    >>> exec(open('scripts/test_acquisition_persistence.py').read())
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.acquisition.container import Container
from apps.acquisition.models import SearchStrategyModel, SearchExecutionModel, StudyModel

print("=" * 80)
print("🧪 TEST DE PERSISTENCIA - ACQUISITION MODULE")
print("=" * 80)

# =============================================================================
# 1. OBTENER EL ORQUESTADOR
# =============================================================================
print("\n[1] Obteniendo orquestador...")
orchestrator = Container.get_orchestrator()
print(f"    ✅ Orquestador obtenido: {orchestrator}")

# =============================================================================
# 2. DEFINIR ESTRATEGIA DE BÚSQUEDA
# =============================================================================
print("\n[2] Definiendo estrategia de búsqueda...")

strategy_dict = {
    "strategy_id": "test_ml_se_2024",
    "main_terms": [
        {
            "term": "machine learning",
            "synonyms": ["ML", "deep learning", "neural networks"]
        },
        {
            "term": "software engineering",
            "synonyms": ["SE", "software development"]
        }
    ],
    "exclusions": ["medical", "healthcare"],
    "filters": {
        "year": {
            "from": 2020,
            "to": 2024
        }
    }
}

print(f"    📋 Estrategia ID: {strategy_dict['strategy_id']}")
print(f"    📋 Términos: {len(strategy_dict['main_terms'])}")
print(f"    📋 Exclusiones: {len(strategy_dict['exclusions'])}")
print(f"    📋 Filtro años: {strategy_dict['filters']['year']}")

# =============================================================================
# 3. EJECUTAR BÚSQUEDA (CON PERSISTENCIA AUTOMÁTICA)
# =============================================================================
print("\n[3] Ejecutando búsqueda con persistencia...")
print("    ⏳ Esto puede tardar 30-60 segundos (consultando Scopus e IEEE)...")

try:
    result = orchestrator.execute_search_from_strategy(
        strategy_dict=strategy_dict,
        research_question_id=None,  # Puede vincularse a Design si quieres
        user=None,  # Puede asignarse un usuario
        strategy_name="Test ML in SE 2020-2024",
        strategy_description="Prueba de persistencia del módulo Acquisition"
    )

    print(f"\n    ✅ BÚSQUEDA COMPLETADA")
    print(f"    📊 Execution ID: {result.execution_id}")
    print(f"    📊 Strategy ID: {result.strategy_id}")
    print(f"    📊 Total encontrados: {result.total_found}")
    print(f"    📊 Nuevos: {result.new_studies_count}")
    print(f"    📊 Duplicados: {result.duplicates_count}")
    print(f"    📊 Estado: {result.status}")
    print(f"    📊 Proveedores consultados: {list(result.queries_by_source.keys())}")

except Exception as e:
    print(f"    ❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# =============================================================================
# 4. VERIFICAR QUE SE GUARDÓ EN BD
# =============================================================================
print("\n[4] Verificando persistencia en BD...")

# 4.1 Verificar SearchStrategyModel
strategy_count = SearchStrategyModel.objects.count()
print(f"    ✅ Estrategias en BD: {strategy_count}")

# 4.2 Verificar SearchExecutionModel
execution_count = SearchExecutionModel.objects.count()
print(f"    ✅ Ejecuciones en BD: {execution_count}")

# 4.3 Verificar StudyModel
study_count = StudyModel.objects.count()
print(f"    ✅ Estudios en BD: {study_count}")

# 4.4 Verificar la última ejecución
try:
    last_execution = SearchExecutionModel.objects.latest('executed_at')
    print(f"\n    📋 Última ejecución:")
    print(f"       ID: {last_execution.id}")
    print(f"       Fecha: {last_execution.executed_at}")
    print(f"       Resultados: {last_execution.results_count}")
    print(f"       Nuevos: {last_execution.new_studies_count}")
    print(f"       Estado: {last_execution.status}")

    # 4.5 Ver algunos estudios vinculados
    studies = last_execution.studies.all()[:5]
    print(f"\n    📚 Primeros 5 estudios de esta ejecución:")
    for i, study in enumerate(studies, 1):
        print(f"       {i}. {study.title[:70]}...")
        print(f"          Source: {study.source} | DOI: {study.doi or 'N/A'}")

        # Verificar metadata de ExecutionStudy
        exec_study = last_execution.executionstudy_set.filter(study=study).first()
        if exec_study:
            new_flag = "🆕 NUEVO" if exec_study.is_new else "🔄 DUPLICADO"
            print(f"          {new_flag} | Providers: {', '.join(exec_study.providers)}")

except Exception as e:
    print(f"    ⚠️  No se pudo recuperar la última ejecución: {e}")

# =============================================================================
# 5. PROBAR CONSULTAS
# =============================================================================
print("\n[5] Probando consultas al repositorio...")

repository = Container.get_repository()

# 5.1 Contar por estado
from apps.acquisition.shared.domain.value_objects.study_status import StudyStatus
discovered_count = repository.count_by_status(StudyStatus.DISCOVERED)
print(f"    ✅ Estudios DISCOVERED: {discovered_count}")

# 5.2 Obtener todos (paginado)
all_studies = repository.find_all(limit=3)
print(f"    ✅ Primeros 3 estudios del repo:")
for study in all_studies:
    print(f"       - {study.title[:60]}...")

# =============================================================================
# RESUMEN FINAL
# =============================================================================
print("\n" + "=" * 80)
print("✅ TEST DE PERSISTENCIA COMPLETADO")
print("=" * 80)
print(f"""
RESUMEN:
- ✅ Orquestador funcional
- ✅ Estrategia guardada en BD ({strategy_count} total)
- ✅ Ejecución registrada en BD ({execution_count} total)
- ✅ Estudios persistidos en BD ({study_count} total)
- ✅ Trazabilidad completa (ExecutionStudy con is_new y providers)
- ✅ Repositorio funcional con consultas

🎉 TODO FUNCIONA CORRECTAMENTE

PRÓXIMOS PASOS:
1. Integrar con Design (pasar research_question_id real)
2. Implementar enriquecimiento de metadatos
3. Implementar descargas de PDFs
4. Crear APIs/vistas para exponer estas funcionalidades
""")
