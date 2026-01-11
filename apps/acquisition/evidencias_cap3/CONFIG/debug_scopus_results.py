import os
import sys
import django

sys.path.append(r"d:\Tesis\ADN4RESEARCH")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.acquisition.models import ExecutionStudy

def check_scopus():
    target_execs = [
        'bad12477-31c4-4cad-b740-ae79a195d50e', 
        'b212990a-096c-4f9b-90e0-f536496aa2ec'
    ]
    
    print("Checking Providers in Pilot Executions...")
    for eid in target_execs:
        links = ExecutionStudy.objects.filter(execution_id=eid)
        print(f"\nExecution: {eid}")
        print(f"Total Links: {links.count()}")
        
        provider_counts = {}
        for link in links:
            for p in link.providers:
                provider_counts[p] = provider_counts.get(p, 0) + 1
        
        for p, count in provider_counts.items():
            print(f"  - {p}: {count}")

if __name__ == "__main__":
    check_scopus()
