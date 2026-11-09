import sqlite3
import os
import datetime

db_path = 'db.sqlite3'
if os.path.exists(db_path):
    print("Checking db.sqlite3 schema for permits_customuser.designation...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(permits_customuser)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'designation' not in columns:
        print("Adding column designation to permits_customuser table...")
        cursor.execute("ALTER TABLE permits_customuser ADD COLUMN designation varchar(150) NOT NULL DEFAULT ''")
        conn.commit()
        print("Successfully added designation column.")
    else:
        print("Column designation already exists in permits_customuser.")
    
    # Check if migration 0021 is recorded in django_migrations
    cursor.execute("SELECT id FROM django_migrations WHERE app='permits' AND name='0021_customuser_designation_alter_customuser_role'")
    if not cursor.fetchone():
        now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
        cursor.execute(
            "INSERT INTO django_migrations (app, name, applied) VALUES ('permits', '0021_customuser_designation_alter_customuser_role', ?)",
            (now,)
        )
        conn.commit()
        print("Recorded migration 0021 in django_migrations table.")
        
    conn.close()
