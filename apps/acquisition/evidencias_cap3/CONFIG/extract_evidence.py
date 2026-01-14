import os
import sys
import django
import json
from django.core.serializers.json import DjangoJSONEncoder

# Setup Django Environment
sys.path.append(r"d:\Tesis\ADN4RESEARCH")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.acquisition.models import StudyModel, SearchExecutionModel, ExecutionStudy

def export_evidence():
    base_dir = r"d:\Tesis\ADN4RESEARCH\evidencias_cap3\DB_EXPORTS"
    
    print("Exporting Traceability Evidence (Aligned)...")

    # 1. SearchExecution (Figure 3.1)
    # We target the "PILOT_02_DEVOPS" strategy execution which we know has results
    # Or just the latest SUCCESS execution that has results
    target_exec = SearchExecutionModel.objects.filter(results_count__gt=0).order_by('-executed_at').first()
    
    if target_exec:
        print(f"[OK] Found Target Execution: {target_exec.id} (Date: {target_exec.executed_at})")
        
        # Fig 3.1
        data_exec = {
            "id": str(target_exec.id),
            "executed_at": target_exec.executed_at,
            "results_count": target_exec.results_count,
            "status": target_exec.status,
            "translated_queries": target_exec.translated_queries
        }
        with open(os.path.join(base_dir, "fig_3_1_search_execution.json"), "w", encoding="utf-8") as f:
            json.dump(data_exec, f, indent=2, cls=DjangoJSONEncoder)
        print(f"[OK] Exported Fig 3.1")
        
        # 2. ExecutionStudy (Figure 3.3) - LINK
        # Find a link belonging to THIS execution
        link = ExecutionStudy.objects.filter(execution=target_exec).first()
        
        target_study = None # To hold the study for Fig 3.2
        
        if link:
            data_link = {
                "execution_id": str(link.execution_id),
                "study_id": str(link.study_id),
                "is_new": link.is_new,
                "providers": link.providers,
                "rank_position": link.rank_position,
                "linked_at": link.linked_at
            }
            with open(os.path.join(base_dir, "fig_3_3_execution_study.json"), "w", encoding="utf-8") as f:
                json.dump(data_link, f, indent=2, cls=DjangoJSONEncoder)
            print(f"[OK] Exported Fig 3.3 (Link)")
            
            target_study = link.study
        else:
            print("[WARN] No ExecutionStudy link found for this execution.")
            
        # 3. StudyModel (Figure 3.2)
        # Use the study from the link if available, otherwise fallback
        if target_study:
            data_study = {
                "uuid": str(target_study.uuid),
                "title": target_study.title,
                "status": target_study.status,
                "consolidation_status": target_study.consolidation_status,
                "download_status": target_study.download_status,
                "field_origins": target_study.field_origins,
                "pdf_source": target_study.pdf_source
            }
            with open(os.path.join(base_dir, "fig_3_2_study_traceability.json"), "w", encoding="utf-8") as f:
                json.dump(data_study, f, indent=2, cls=DjangoJSONEncoder)
            print(f"[OK] Exported Fig 3.2 (Study: {target_study.title[:30]}...)")
        else:
            print("[WARN] No Study found linked to execution.")

    else:
        print("[WARN] No valid SearchExecution found with results.")


if __name__ == "__main__":
    export_evidence()
