import json
import os
import textwrap

def generate_figures():
    base_dir = r"d:\Tesis\ADN4RESEARCH\evidencias_cap3"
    exports_dir = os.path.join(base_dir, "DB_EXPORTS")
    figures_dir = os.path.join(base_dir, "FIGURAS")
    
    # Ensure FIGURAS exists
    os.makedirs(figures_dir, exist_ok=True)
    
    print("Generating simulated figures from JSON data...")

    # --- Figure 3.1: Search Execution Detail ---
    with open(os.path.join(exports_dir, "fig_3_1_search_execution.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
    
    fig_3_1 = f"""
    ================================================================================
                                ADN4RESEARCH - ADMIN PANEL
    ================================================================================
    [SEARCH EXECUTION DETAIL]                                     Status: {data.get("status")}
    --------------------------------------------------------------------------------
    Execution ID    : {data.get("id")}
    Executed At     : {data.get("executed_at")}
    Total Results   : {data.get("results_count")}
    
    [TRANSLATED QUERIES]
    --------------------------------------------------------------------------------
    """
    for source, query in data.get("translated_queries", {}).get("queries_by_source", {}).items():
        fig_3_1 += f"    > Source: {source}\n"
        fig_3_1 += f"      Query : {query}\n\n"
        
    with open(os.path.join(figures_dir, "fig_3_1_admin_view.txt"), "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(fig_3_1))
    print("[OK] fig_3_1_admin_view.txt created.")


    # --- Figure 3.2: Study Detail ---
    with open(os.path.join(exports_dir, "fig_3_2_study_traceability.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
        
    fig_3_2 = f"""
    ================================================================================
                                ADN4RESEARCH - STUDY DETAIL
    ================================================================================
    UUID          : {data.get("uuid")}
    Title         : {data.get("title")}
    
    [WORKFLOW STATUS]
    --------------------------------------------------------------------------------
    Global Status : {data.get("status")}
    Consolidation : {data.get("consolidation_status")}
    Download      : {data.get("download_status")} (Source: {data.get("pdf_source")})
    
    [DATA PROVENANCE (Field Origins)]
    --------------------------------------------------------------------------------
    """
    for field, origin in data.get("field_origins", {}).items():
        fig_3_2 += f"    {field:<15} : {origin.upper()}\n"
        
    with open(os.path.join(figures_dir, "fig_3_2_study_view.txt"), "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(fig_3_2))
    print("[OK] fig_3_2_study_view.txt created.")

    # --- Figure 3.3: Execution Link ---
    with open(os.path.join(exports_dir, "fig_3_3_execution_study.json"), "r", encoding="utf-8") as f:
        data = json.load(f)

    fig_3_3 = f"""
    ================================================================================
                            ADN4RESEARCH - TRACEABILITY LINK
    ================================================================================
    [LINK RECORD]
    --------------------------------------------------------------------------------
    Execution ID  : {data.get("execution_id")}
    Study ID      : {data.get("study_id")}
    
    Is New Study? : {data.get("is_new")}
    Linked At     : {data.get("linked_at")}
    Rank Position : {data.get("rank_position")}
    
    Found In Providers:
    {data.get("providers")}
    """
    with open(os.path.join(figures_dir, "fig_3_3_link_view.txt"), "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(fig_3_3))
    print("[OK] fig_3_3_link_view.txt created.")

if __name__ == "__main__":
    generate_figures()
