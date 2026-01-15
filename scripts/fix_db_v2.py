from django.db import connection

def fix():
    with connection.cursor() as cursor:
        print(f"Vendor: {connection.vendor}")
        engine = connection.vendor
        
        if engine == 'sqlite':
            cursor.execute("PRAGMA table_info(project_project)")
            cols = [r[1] for r in cursor.fetchall()]
        else:
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='project_project'")
            cols = [r[0] for r in cursor.fetchall()]
        
        print(f"Cols: {cols}")
        
        if 'name' in cols:
            cursor.execute("ALTER TABLE project_project RENAME COLUMN name TO title")
            print("Renamed name -> title")
            
        if 'description' in cols:
            cursor.execute("ALTER TABLE project_project RENAME COLUMN description TO summary")
            print("Renamed description -> summary")

        if 'motivation' not in cols:
            cursor.execute("ALTER TABLE project_project ADD COLUMN motivation text DEFAULT '' NOT NULL")
            print("Added motivation")

        if 'general_objective' not in cols:
            cursor.execute("ALTER TABLE project_project ADD COLUMN general_objective text DEFAULT '' NOT NULL")
            print("Added general_objective")

fix()
