
import sqlite3

DB_PATH = 'pmt_app/pm_tool.db'

def cleanup():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Usernames to remove (placeholders and defaults)
    to_remove = ['admin', 'user', 'john_pm', 'jane_exec', 'bob_recorder']
    
    # Also remove by full name patterns if usernames differ
    full_names_to_remove = ['John Project Manager', 'Jane Executive', 'Bob Recorder']
    
    for uname in to_remove:
        cursor.execute("DELETE FROM users WHERE username = ?", (uname,))
    
    for fname in full_names_to_remove:
        cursor.execute("DELETE FROM users WHERE full_name = ?", (fname,))
        
    conn.commit()
    conn.close()
    print("Cleanup complete. Placeholder users removed.")

if __name__ == "__main__":
    cleanup()
