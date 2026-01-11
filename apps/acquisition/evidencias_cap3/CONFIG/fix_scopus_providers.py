import os
import sys
import django

# Setup path
sys.path.append(r"d:\Tesis\ADN4RESEARCH")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.acquisition.models import ExecutionStudy

def fix_providers():
    eid = 'b212990a-096c-4f9b-90e0-f536496aa2ec'
    print(f"Fixing Providers for Execution: {eid}")
    
    links = ExecutionStudy.objects.filter(execution_id=eid)
    
    if not links.exists():
        print("[ERROR] No links found! Check Execution ID.")
        return

    count = 0
    for link in links:
        # Force list assignment
        current = link.providers if isinstance(link.providers, list) else []
        
        if "Scopus" not in current:
            # Create a clean new list
            new_providers = ["Scopus", "IEEE Xplore"]
            link.providers = new_providers
            link.save()
            print(f"Updated Study {link.study.uuid}: {new_providers}")
            count += 1
        else:
             print(f"Study {link.study.uuid} had Scopus: {current}")

    print(f"Fixed {count} records.")
    
    # Verification
    print("\nVerifying...")
    for link in ExecutionStudy.objects.filter(execution_id=eid):
        print(f" - {link.study.title[:20]}... : {link.providers}")

if __name__ == "__main__":
    try:
        fix_providers()
    except Exception as e:
        print(f"An error occurred: {e}")
