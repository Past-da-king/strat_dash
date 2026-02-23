
import sqlite3
from werkzeug.security import generate_password_hash
import os

DB_PATH = 'pmt_app/pm_tool.db'

def setup_users_v2():
    # User Request Mapping:
    # info -> Sinqobile (Executive)
    # finance -> Nkululeko (Recorder)
    # bonganis -> Bongani (PM)
    # operations -> Sphelele (Recorder)
    # technical -> Ayanda (Admin)
    
    users = [
        ('info@strategyedge.co.za', 'Sinqobile', 'sinqobile@strat', 'executive', 'Sinqobile'),
        ('finance@strategyedge.co.za', 'Nkululeko', 'nkululeko@strat', 'recorder', 'Nkululeko'),
        ('bonganis@strategyedge.co.za', 'Bongani', 'Bongani@strat', 'pm', 'Bongani'),
        ('operations@strategyedge.co.za', 'Sphelele', 'sphelele@strat', 'recorder', 'Sphelele'),
        ('technical@strategyedge.co.za', 'Ayanda', 'ayanda@strat', 'admin', 'Ayanda')
    ]
    
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for email, username, password, role, full_name in users:
        password_hash = generate_password_hash(password)
        
        # Check if user exists by email (the unique identifier we've been using)
        # However, the user wants 'username' to be the new name.
        # Let's delete old entries for these emails to avoid conflict and re-insert with new usernames.
        cursor.execute("DELETE FROM users WHERE username = ?", (email,))
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        
        print(f"Creating/Updating user: {username} (Role: {role}, Pass: {password})")
        cursor.execute("""
            INSERT INTO users (username, password_hash, role, full_name, status)
            VALUES (?, ?, ?, ?, 'approved')
        """, (username, password_hash, role, full_name))
            
    conn.commit()
    conn.close()
    print("\nUser update v2 complete.")

if __name__ == "__main__":
    setup_users_v2()
