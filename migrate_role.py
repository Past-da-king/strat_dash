
import sqlite3
import os

DB_PATH = 'pmt_app/pm_tool.db'

def rename_role():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Update users table
    print("Updating users table: renaming 'recorder' to 'team'...")
    cursor.execute("UPDATE users SET role = 'team' WHERE role = 'recorder'")
    
    # 2. Update project_assignments table (if any)
    print("Updating project_assignments: renaming 'recorder' to 'team'...")
    cursor.execute("UPDATE project_assignments SET assigned_role = 'team' WHERE assigned_role = 'recorder'")
    
    conn.commit()
    conn.close()
    print("Database migration complete.")

if __name__ == "__main__":
    rename_role()
