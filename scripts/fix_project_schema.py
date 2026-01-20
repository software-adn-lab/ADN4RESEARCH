import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def fix_schema():
    with connection.cursor() as cursor:
        engine = connection.vendor
        print(f"Database vendor: {engine}")

        if engine == 'sqlite':
            cursor.execute("PRAGMA table_info(project_project)")
            columns_info = cursor.fetchall()  # list of tuples (cid, name, type, notnull, dflt_value, pk)
            columns = [col[1] for col in columns_info]
        else:
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='project_project';")
            columns = [row[0] for row in cursor.fetchall()]

        print(f"Current columns: {columns}")

        if 'name' in columns:
            print("Renaming 'name' to 'title'...")
            cursor.execute("ALTER TABLE project_project RENAME COLUMN name TO title;")
        
        if 'description' in columns:
            print("Renaming 'description' to 'summary'...")
            cursor.execute("ALTER TABLE project_project RENAME COLUMN description TO summary;")

        # Refresh columns
        if engine == 'sqlite':
            cursor.execute("PRAGMA table_info(project_project)")
            columns = [col[1] for col in cursor.fetchall()]
        else:
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='project_project';")
            columns = [row[0] for row in cursor.fetchall()]

        if 'motivation' not in columns:
            print("Adding 'motivation' column...")
            cursor.execute("ALTER TABLE project_project ADD COLUMN motivation text DEFAULT '' NOT NULL;")
            
        if 'general_objective' not in columns:
            print("Adding 'general_objective' column...")
            cursor.execute("ALTER TABLE project_project ADD COLUMN general_objective text DEFAULT '' NOT NULL;")

        print("Schema fix completed.")

if __name__ == '__main__':
    fix_schema()
