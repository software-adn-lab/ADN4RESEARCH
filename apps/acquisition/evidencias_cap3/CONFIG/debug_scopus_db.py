import os
import sys
import django

sys.path.append(r"d:\Tesis\ADN4RESEARCH")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.acquisition.models import ExecutionStudy

def check_db():
    eid = 'b212990a-096c-4f9b-90e0-f536496aa2ec'
    print(f"Checking Execution: {eid}")
    
    links = ExecutionStudy.objects.filter(execution_id=eid)
    print(f"Found {links.count()} links.")
    
    for i, link in enumerate(links):
        print(f"Link {i+1}: Study={link.study.title[:30]}... | Providers={link.providers} | Type={type(link.providers)}")

if __name__ == "__main__":
    check_db()
