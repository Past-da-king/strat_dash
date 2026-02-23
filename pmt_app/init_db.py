import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pm_tool.db')
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Old database removed.")

    # Ensure uploads directory exists
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    print(f"Uploads directory ensured at: {UPLOADS_DIR}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        full_name TEXT NOT NULL,
        status TEXT DEFAULT 'approved'
    )
    ''')

    # 2. Projects Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        project_id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name TEXT NOT NULL,
        project_number TEXT UNIQUE NOT NULL,
        client TEXT,
        pm_user_id INTEGER,
        total_budget REAL,
        start_date DATE,
        target_end_date DATE,
        status TEXT DEFAULT 'active',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        created_by INTEGER,
        FOREIGN KEY (pm_user_id) REFERENCES users (user_id),
        FOREIGN KEY (created_by) REFERENCES users (user_id)
    )
    ''')

    # 3. Baseline Schedule Table (UPDATED: added responsible_user_id, expected_output)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS baseline_schedule (
        activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        activity_name TEXT NOT NULL,
        planned_start DATE,
        planned_finish DATE,
        budgeted_cost REAL,
        depends_on INTEGER,
        responsible_user_id INTEGER,
        expected_output TEXT,
        status TEXT DEFAULT 'Not Started',
        sort_order INTEGER,
        FOREIGN KEY (project_id) REFERENCES projects (project_id),
        FOREIGN KEY (responsible_user_id) REFERENCES users (user_id)
    )
    ''')

    # 4. Activity Log Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS activity_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        activity_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        event_date DATE NOT NULL,
        recorded_by INTEGER NOT NULL,
        recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (activity_id) REFERENCES baseline_schedule (activity_id),
        FOREIGN KEY (recorded_by) REFERENCES users (user_id)
    )
    ''')

    # 5. Expenditure Log Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS expenditure_log (
        exp_id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        activity_id INTEGER,
        category TEXT NOT NULL,
        description TEXT,
        reference_id TEXT,
        amount REAL NOT NULL,
        spend_date DATE NOT NULL,
        recorded_by INTEGER NOT NULL,
        recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        approved_by INTEGER,
        approved_at DATETIME,
        FOREIGN KEY (project_id) REFERENCES projects (project_id),
        FOREIGN KEY (activity_id) REFERENCES baseline_schedule (activity_id),
        FOREIGN KEY (recorded_by) REFERENCES users (user_id),
        FOREIGN KEY (approved_by) REFERENCES users (user_id)
    )
    ''')

    # 6. Project Assignments (Many-to-Many)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS project_assignments (
        assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        assigned_role TEXT,
        assigned_by INTEGER,
        assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects (project_id),
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        FOREIGN KEY (assigned_by) REFERENCES users (user_id),
        UNIQUE(project_id, user_id)
    )
    ''')

    # 7. Audit Log Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS audit_log (
        audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_name TEXT NOT NULL,
        record_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        old_value TEXT,
        new_value TEXT,
        changed_by INTEGER NOT NULL,
        changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (changed_by) REFERENCES users (user_id)
    )
    ''')

    # 8. Risks & Issues Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS risks (
        risk_id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        date_identified DATE,
        description TEXT NOT NULL,
        impact TEXT,
        status TEXT DEFAULT 'Open',
        mitigation_action TEXT,
        recorded_by INTEGER,
        recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects (project_id),
        FOREIGN KEY (recorded_by) REFERENCES users (user_id)
    )
    ''')

    # 9. Task Outputs Table (NEW)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS task_outputs (
        output_id INTEGER PRIMARY KEY AUTOINCREMENT,
        activity_id INTEGER NOT NULL,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        uploaded_by INTEGER NOT NULL,
        FOREIGN KEY (activity_id) REFERENCES baseline_schedule (activity_id),
        FOREIGN KEY (uploaded_by) REFERENCES users (user_id)
    )
    ''')

    # Seed Admin User
    admin_pw = generate_password_hash('admin123')
    cursor.execute('''
    INSERT INTO users (username, password_hash, role, full_name)
    VALUES (?, ?, ?, ?)
    ''', ('admin', admin_pw, 'admin', 'System Administrator'))

    # Seed Some roles for testing
    pm_pw = generate_password_hash('pm123')
    cursor.execute('''
    INSERT INTO users (username, password_hash, role, full_name)
    VALUES (?, ?, ?, ?)
    ''', ('pm_user', pm_pw, 'pm', 'John Project Manager'))

    exec_pw = generate_password_hash('exec123')
    cursor.execute('''
    INSERT INTO users (username, password_hash, role, full_name)
    VALUES (?, ?, ?, ?)
    ''', ('exec_user', exec_pw, 'executive', 'Jane Executive'))

    rec_pw = generate_password_hash('rec123')
    cursor.execute('''
    INSERT INTO users (username, password_hash, role, full_name)
    VALUES (?, ?, ?, ?)
    ''', ('recorder', rec_pw, 'recorder', 'Bob Recorder'))

    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")
    print(f"Tables created: users, projects, baseline_schedule, activity_log, expenditure_log, project_assignments, audit_log, risks, task_outputs")

if __name__ == '__main__':
    init_db()
