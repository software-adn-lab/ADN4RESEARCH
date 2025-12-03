"""
Ejemplo de cómo Design usa el facade para preview + finalize
"""

from apps.acquisition.facade import get_acquisition_facade
from django.contrib.auth import get_user_model

User = get_user_model()

def ejemplo_flujo_completo():
    """Ejemplo completo del flujo Design → Acquisition"""
    
    facade = get_acquisition_facade()
    
    # ========================================
    # PASO 1: PREVIEW (sin persistir)
    # ========================================
    
    strategy_dict = {
        "main_terms": [
            {
                "term": "machine learning",
                "synonyms": ["ML", "deep learning", "artificial intelligence"]
            },
            {
                "term": "software quality",
                "synonyms": ["code quality", "software metrics"]
            }
        ],
        "exclusions": [
            "medical applications",
            "gaming",
            "mobile apps"
        ],
        "filters": {
            "year": {
                "from": 2020,
                "to": 2024
            }
        }
    }
    
    print("🔍 PASO 1: Preview Search")
    print("=" * 50)
    
    preview_result = facade.preview_search(
        strategy_dict=strategy_dict,
        max_results_per_source=30  # Más estudios para elegir
    )
    
    print(f"📊 Resultados del preview:")
    print(f"   Total encontrado: {preview_result.total_found}")
    print(f"   Queries ejecutadas: {list(preview_result.queries_by_source.keys())}")
    
    if preview_result.total_found == 0:
        print("❌ No se encontraron estudios")
        return
    
    # Mostrar algunos estudios al "usuario"
    print(f"\n📚 Primeros 5 estudios encontrados:")
    for i, study in enumerate(preview_result.studies[:5]):
        print(f"   {i+1}. {study['title'][:60]}...")
        print(f"      Fuente: {study['source']} | Año: {study['year']}")
        print(f"      Open Access: {study['is_open_access']}")
        print()
    
    # ========================================
    # PASO 2: USUARIO SELECCIONA ESTUDIOS
    # ========================================
    
    print("👤 PASO 2: Usuario selecciona estudios relevantes")
    print("=" * 50)
    
    # Simular selección del usuario (en la realidad sería UI)
    # Criterios: Open Access + años recientes + fuentes confiables
    selected_studies = []
    
    for study in preview_result.studies:
        # Criterios de selección automática (simulando usuario)
        if (study.get('year', 0) >= 2022 and 
            study.get('is_open_access') == True and
            len(selected_studies) < 8):  # Máximo 8 estudios
            selected_studies.append(study)
    
    # Si no hay suficientes Open Access, tomar los más recientes
    if len(selected_studies) < 5:
        recent_studies = [s for s in preview_result.studies 
                         if s.get('year', 0) >= 2022][:8]
        selected_studies = recent_studies
    
    print(f"✅ Usuario seleccionó {len(selected_studies)} estudios:")
    for i, study in enumerate(selected_studies):
        print(f"   {i+1}. {study['title'][:50]}... ({study['source']})")
    
    # ========================================
    # PASO 3: FINALIZE (persistir)
    # ========================================
    
    print(f"\n💾 PASO 3: Finalize Search (persistir)")
    print("=" * 50)
    
    # En la realidad, este ID vendría de la SearchStrategy creada en Design
    design_strategy_id = 1  # Mock ID
    
    # Obtener usuario (en la realidad vendría del request)
    try:
        user = User.objects.first()  # Mock user
    except:
        user = None
    
    # Filtrar estudios seleccionados en el preview_result
    preview_result.studies = selected_studies
    
    final_result = facade.finalize_search(
        design_strategy_id=design_strategy_id,
        preview_result=preview_result,
        user=user
    )
    
    print(f"🎉 FINALIZACIÓN EXITOSA:")
    print(f"   Execution ID: {final_result.execution_id}")
    print(f"   Strategy ID: {final_result.strategy_id}")
    print(f"   Estudios persistidos: {len(final_result.studies_persisted)}")
    print(f"   Nuevos estudios: {final_result.new_studies_count}")
    print(f"   Duplicados detectados: {final_result.duplicates_count}")
    print(f"   Ejecutado en: {final_result.executed_at}")
    print(f"   Estado: {final_result.status}")
    
    print(f"\n📋 IDs de estudios persistidos:")
    for study_id in final_result.studies_persisted:
        print(f"   - {study_id}")
    
    return final_result

def ejemplo_uso_en_vista_django():
    """Ejemplo de cómo se usaría en una vista de Django"""
    
    # En views.py del módulo Design
    from django.http import JsonResponse
    from django.views.decorators.csrf import csrf_exempt
    import json
    
    @csrf_exempt
    def search_preview(request):
        """Vista para preview de búsqueda"""
        if request.method == 'POST':
            strategy_dict = json.loads(request.body)
            
            facade = get_acquisition_facade()
            preview_result = facade.preview_search(
                strategy_dict=strategy_dict,
                max_results_per_source=25
            )
            
            return JsonResponse({
                'total_found': preview_result.total_found,
                'queries_by_source': preview_result.queries_by_source,
                'studies': preview_result.studies
            })
    
    @csrf_exempt 
    def search_finalize(request):
        """Vista para finalizar y persistir búsqueda"""
        if request.method == 'POST':
            data = json.loads(request.body)
            
            facade = get_acquisition_facade()
            
            # Reconstruir preview_result desde data
            preview_result = PreviewSearchResult(
                queries_by_source=data['queries_by_source'],
                total_found=len(data['selected_studies']),
                studies=data['selected_studies'],
                strategy_dict=data['strategy_dict']
            )
            
            final_result = facade.finalize_search(
                design_strategy_id=data['design_strategy_id'],
                preview_result=preview_result,
                user=request.user
            )
            
            return JsonResponse({
                'execution_id': final_result.execution_id,
                'studies_persisted': final_result.studies_persisted,
                'new_studies_count': final_result.new_studies_count,
                'status': final_result.status
            })

if __name__ == "__main__":
    # Configurar Django
    import os
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    
    # Ejecutar ejemplo
    ejemplo_flujo_completo()