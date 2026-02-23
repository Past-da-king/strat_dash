
import sqlite3
from werkzeug.security import generate_password_hash
import os

DB_PATH = 'pmt_app/pm_tool.db'

def fix_siphelele():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    old_username = 'Sphelele'
    new_username = 'Siphelele'
    new_password = 'siphelele@strat'
    new_display_name = 'Siphelele'
    
    password_hash = generate_password_hash(new_password)
    
    # Check if old user exists
    cursor.execute("SELECT user_id FROM users WHERE username = ?", (old_username,))
    row = cursor.fetchone()
    
    if row:
        user_id = row[0]
        print(f"Updating {old_username} (ID: {user_id}) to {new_username}...")
        cursor.execute("""
            UPDATE users 
            SET username = ?, password_hash = ?, full_name = ?
            WHERE user_id = ?
        """, (new_username, password_hash, new_display_name, user_id))
    else:
        # If Sphelele doesn't exist, maybe it was already deleted or never created.
        # Let's ensure Siphelele exists regardless.
        cursor.execute("SELECT user_id FROM users WHERE username = ?", (new_username,))
        if not cursor.fetchone():
            print(f"Creating new user {new_username}...")
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, full_name, status)
                VALUES (?, ?, 'recorder', ?, 'approved')
            """, (new_username, password_hash, new_display_name))
        else:
            print(f"User {new_username} already exists. Updating password...")
            cursor.execute("""
                UPDATE users SET password_hash = ? WHERE username = ?
            """, (password_hash, new_username))
            
    conn.commit()
    conn.close()
    print("Update complete.")

if __name__ == "__main__":
    fix_siphelele()
