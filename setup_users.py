
import sqlite3
import hashlib
import os

DB_PATH = 'pmt_app/pm_tool.db'

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def setup_users():
    users = [
        ('info@strategyedge.co.za', 'info', 'executive', 'Strategy Edge Executive'),
        ('technical@strategyedge.co.za', 'technical', 'admin', 'Strategy Edge Admin'),
        ('finance@strategyedge.co.za', 'finance', 'recorder', 'Strategy Edge Finance'),
        ('operations@strategyedge.co.za', 'operations', 'recorder', 'Strategy Edge Operations'),
        ('bonganis@strategyedge.co.za', 'bongani', 'pm', 'Bongani S.')
    ]
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for email, prefix, role, name in users:
        username = email
        password = f"{prefix}$002"
        password_hash = hash_password(password)
        
        # Check if user exists
        cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        exists = cursor.fetchone()
        
        if exists:
            print(f"Updating user: {username} (Role: {role}, Pass: {password})")
            cursor.execute("""
                UPDATE users 
                SET password_hash = ?, role = ?, full_name = ?, status = 'approved'
                WHERE username = ?
            """, (password_hash, role, name, username))
        else:
            print(f"Creating user: {username} (Role: {role}, Pass: {password})")
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, full_name, status)
                VALUES (?, ?, ?, ?, 'approved')
            """, (username, password_hash, role, name))
            
    conn.commit()
    conn.close()
    print("\nUser setup complete.")

if __name__ == "__main__":
    setup_users()
