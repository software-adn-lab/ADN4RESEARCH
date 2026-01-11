import os
import sys
import django
import json

# Setup Django Environment
sys.path.append(r"d:\Tesis\ADN4RESEARCH")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.acquisition.models import StudyModel, SearchExecutionModel, ExecutionStudy

def print_header(title):
    print(f"\n{'='*50}")
    print(f"GENERATING: {title}")
    print(f"{'='*50}")

def run_filtered_metrics():
    # Target specific executions from our Pilot run (2025-12-28)
    # IDs taken from pilot_output.txt
    TARGET_EXEC_IDS = [
        'bad12477-31c4-4cad-b740-ae79a195d50e', # Strategy 1: ML & SE
        'b212990a-096c-4f9b-90e0-f536496aa2ec'  # Strategy 2: DevOps
    ]
    
    print(f"Filtering dataset for Pilot Executions: {TARGET_EXEC_IDS}")
    print("Including Manual Control Study...")
    
    # 1. Get Studies from Executions
    pilot_studies_ids = ExecutionStudy.objects.filter(execution_id__in=TARGET_EXEC_IDS).values_list('study_id', flat=True)
    
    # 2. Get Manual Control Study
    # Note: Using filter() to avoid crash if not found
    manual_studies_ids = StudyModel.objects.filter(title__icontains="Manual Fallback Mechanisms").values_list('uuid', flat=True)
    
    # Combine
    all_target_ids = list(pilot_studies_ids) + list(manual_studies_ids)
    
    # Create the QuerySet for metrics
    target_studies = StudyModel.objects.filter(uuid__in=all_target_ids)
    
    total_eval = target_studies.count()
    print(f"\n[DATASET DEFINITION]")
    print(f"Total Evaluated Studies: {total_eval}")
    print(f"  - From Pilots: {len(pilot_studies_ids)}")
    print(f"  - From Manual Control: {len(manual_studies_ids)}")
    
    # Pass this queryset to metric functions
    metrics_discovery(TARGET_EXEC_IDS)
    metrics_consolidation(target_studies)
    metrics_field_origins(target_studies)
    metrics_full_text(target_studies)
    metrics_pdf_source(target_studies)
    
    # CSV Export for DevOps Pilot
    generate_pilot_details_csv('b212990a-096c-4f9b-90e0-f536496aa2ec')


def metrics_discovery(exec_ids):
    print_header("Tabla 3.2: Resultados de descubrimiento (Piloto 28/12)")
    
    executions = SearchExecutionModel.objects.filter(id__in=exec_ids).order_by('-executed_at')
    
    print(f"{'ExecID':<38} | {'Results':<10} | {'New':<10} | {'Status':<10}")
    print("-" * 80)
    
    for exc in executions:
        print(f"{str(exc.id):<38} | {exc.results_count:<10} | {exc.new_studies_count:<10} | {exc.status:<10}")

def metrics_consolidation(studies):
    print_header("Tabla 3.3: Distribución de ConsolidationStatus")
    
    total = studies.count()
    completo = studies.filter(consolidation_status='completo').count()
    parcial = studies.filter(consolidation_status='parcial').count()
    fallido = studies.filter(consolidation_status='fallido').count()
    
    print(f"Dataset Total: {total}")
    print(f"COMPLETO: {completo} ({(completo/total*100) if total else 0:.1f}%)")
    print(f"PARCIAL:  {parcial} ({(parcial/total*100) if total else 0:.1f}%)")
    print(f"FALLIDO:  {fallido} ({(fallido/total*100) if total else 0:.1f}%)")

def metrics_field_origins(studies):
    print_header("Tabla 3.4: Procedencia de campos (Field Origins)")
    
    # Aggregate counts from target studies
    stats = {} # field -> {auto: 0, manual: 0}
    
    # Only iterate those with field_origins
    relevant = studies.exclude(field_origins={})
    
    for study in relevant:
        origins = study.field_origins
        if not origins: continue
        for field, origin in origins.items():
            if field not in stats: stats[field] = {'auto': 0, 'manual': 0}
            
            # Simple heuristic: 'discovery' or other automated sources vs 'manual'
            if origin == 'manual':
                stats[field]['manual'] += 1
            else:
                stats[field]['auto'] += 1
                
    print(f"{'Field':<20} | {'Auto':<10} | {'Manual':<10}")
    print("-" * 45)
    for field, counts in stats.items():
        print(f"{field:<20} | {counts['auto']:<10} | {counts['manual']:<10}")

def metrics_full_text(studies):
    print_header("Tabla 3.5: Disponibilidad de texto completo")
    
    total = studies.count()
    disponible = studies.filter(download_status='texto_completo_disponible').count()
    no_disponible = studies.filter(download_status='no_disponible').count()
    pendiente = studies.filter(download_status='pendiente').count()
    
    print(f"Dataset Total: {total}")
    print(f"DISPONIBLE:    {disponible}")
    print(f"NO_DISPONIBLE: {no_disponible}")
    print(f"PENDIENTE:     {pendiente}")
    
    if total > 0:
        tasa = (disponible / total) * 100
        print(f"Tasa PDF:      {tasa:.1f}%")

def metrics_pdf_source(studies):
    print_header("Tabla 3.6: Origen del PDF (PdfSource)")
    
    # Filter only available from dataset
    available = studies.filter(download_status='texto_completo_disponible')
    
    sources = {}
    for s in available:
        src = s.pdf_source or "UNKNOWN"
        sources[src] = sources.get(src, 0) + 1
        
    print(f"{'Source':<30} | {'Count':<10}")
    print("-" * 45)
    for src, count in sources.items():
        print(f"{src:<30} | {count:<10}")

def generate_pilot_details_csv(exec_id):
    print_header("Extra: Listado Detallado (Pilot DevOps)")
    
    studies = StudyModel.objects.filter(executionstudy__execution_id=exec_id)
    print(f"Execution: {exec_id}")
    print(f"Format: Title | Providers | Consolidation | Download | PDF Source")
    print("-" * 100)
    
    for s in studies:
        # Get providers via link
        link = ExecutionStudy.objects.filter(study=s, execution_id=exec_id).first()
        providers = ",".join(link.providers) if link else "N/A"
        
        title_short = (s.title[:40] + '..') if len(s.title) > 40 else s.title
        print(f"{title_short:<43} | {providers:<15} | {s.consolidation_status:<10} | {s.download_status:<15} | {s.pdf_source}")

if __name__ == "__main__":
    # Output to file by default to avoid encoding issues in shell redirection
    output_path = r"d:\Tesis\ADN4RESEARCH\evidencias_cap3\DB_EXPORTS\metrics_output.txt"
    
    print(f"Iniciando extracción de métricas (FILTERED) -> {output_path}")
    
    # Redirect stdout to file
    original_stdout = sys.stdout
    with open(output_path, "w", encoding="utf-8") as f:
        sys.stdout = f
        run_filtered_metrics()
        
    sys.stdout = original_stdout
    print("[DONE] Extraction complete and saved to metrics_output.txt.")
