import psycopg2
import os
import streamlit as st
from werkzeug.security import generate_password_hash
import secrets

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

def get_neon_url():
    """Get database URL from Streamlit secrets or environment variable."""
    try:
        return st.secrets["database"]["url"]
    except Exception:
        return os.environ.get("DATABASE_URL")


def get_seed_password(username: str) -> str:
    """
    Get seed password from environment variable or generate secure random one.
    
    Environment variables checked:
    - SEED_ADMIN_PASSWORD
    - SEED_PM_PASSWORD
    - SEED_EXEC_PASSWORD
    - SEED_TEAM_PASSWORD
    
    If not set, generates a secure random password and prints it to console.
    """
    env_mapping = {
        'admin': 'SEED_ADMIN_PASSWORD',
        'pm_user': 'SEED_PM_PASSWORD',
        'exec_user': 'SEED_EXEC_PASSWORD',
        'team_user': 'SEED_TEAM_PASSWORD'
    }
    
    env_var = env_mapping.get(username)
    if env_var:
        password = os.environ.get(env_var)
        if password:
            return password
    
    # Generate secure random password if not set
    return secrets.token_urlsafe(12)

def init_db():
    db_url = get_neon_url()
    if not db_url:
        print("ERROR: No DATABASE_URL found. Set it in .streamlit/secrets.toml or as an env var.")
        return

    # Ensure uploads directory exists
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    print(f"Uploads directory ensured at: {UPLOADS_DIR}")

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id SERIAL PRIMARY KEY,
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
        project_id SERIAL PRIMARY KEY,
        project_name TEXT NOT NULL,
        project_number TEXT UNIQUE NOT NULL,
        client TEXT,
        pm_user_id INTEGER,
        total_budget DOUBLE PRECISION,
        start_date DATE,
        target_end_date DATE,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by INTEGER,
        FOREIGN KEY (pm_user_id) REFERENCES users (user_id),
        FOREIGN KEY (created_by) REFERENCES users (user_id)
    )
    ''')

    # 3. Baseline Schedule Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS baseline_schedule (
        activity_id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL,
        activity_name TEXT NOT NULL,
        planned_start DATE,
        planned_finish DATE,
        budgeted_cost DOUBLE PRECISION,
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
        log_id SERIAL PRIMARY KEY,
        activity_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        event_date DATE NOT NULL,
        recorded_by INTEGER NOT NULL,
        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (activity_id) REFERENCES baseline_schedule (activity_id),
        FOREIGN KEY (recorded_by) REFERENCES users (user_id)
    )
    ''')

    # 5. Expenditure Log Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS expenditure_log (
        exp_id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL,
        activity_id INTEGER,
        category TEXT NOT NULL,
        description TEXT,
        reference_id TEXT,
        amount DOUBLE PRECISION NOT NULL,
        spend_date DATE NOT NULL,
        recorded_by INTEGER NOT NULL,
        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        approved_by INTEGER,
        approved_at TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects (project_id),
        FOREIGN KEY (activity_id) REFERENCES baseline_schedule (activity_id),
        FOREIGN KEY (recorded_by) REFERENCES users (user_id),
        FOREIGN KEY (approved_by) REFERENCES users (user_id)
    )
    ''')

    # 6. Project Assignments (Many-to-Many)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS project_assignments (
        assignment_id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        assigned_role TEXT,
        assigned_by INTEGER,
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects (project_id),
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        FOREIGN KEY (assigned_by) REFERENCES users (user_id),
        UNIQUE(project_id, user_id)
    )
    ''')

    # 7. Audit Logs Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS audit_logs (
        audit_log_id SERIAL PRIMARY KEY,
        user_id INTEGER,
        event_type TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        ip_address TEXT,
        session_fingerprint TEXT,
        metadata TEXT,
        execution_time_ms INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_logs(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_logs(event_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_category ON audit_logs(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_exec_time ON audit_logs(execution_time_ms)")

    # 8. Risks & Issues Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS risks (
        risk_id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL,
        activity_id INTEGER, -- NEW: Link to activity
        date_identified DATE,
        description TEXT NOT NULL,
        impact TEXT,
        status TEXT DEFAULT 'Open',
        mitigation_action TEXT,
        closure_file_path TEXT, -- NEW: Proof of closure
        recorded_by INTEGER,
        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects (project_id),
        FOREIGN KEY (activity_id) REFERENCES baseline_schedule (activity_id),
        FOREIGN KEY (recorded_by) REFERENCES users (user_id)
    )
    ''')

    # 9. Task Outputs Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS task_outputs (
        output_id SERIAL PRIMARY KEY,
        activity_id INTEGER NOT NULL,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        doc_type TEXT DEFAULT 'Draft', -- NEW: First Draft, Regular Draft, Final Document
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        uploaded_by INTEGER NOT NULL,
        FOREIGN KEY (activity_id) REFERENCES baseline_schedule (activity_id),
        FOREIGN KEY (uploaded_by) REFERENCES users (user_id)
    )
    ''')

    # --- PERFORMANCE INDEXES ---
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_baseline_project_id ON baseline_schedule(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenditure_project_id ON expenditure_log(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_log_activity_id ON activity_log(activity_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_risks_project_id ON risks(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_assignments_project_id ON project_assignments(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_assignments_user_id ON project_assignments(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_outputs_activity_id ON task_outputs(activity_id)")

    # Seed Admin User (only if not already present)
    cursor.execute("SELECT 1 FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        admin_pw = get_seed_password('admin')
        cursor.execute('''
        INSERT INTO users (username, password_hash, role, full_name)
        VALUES (%s, %s, %s, %s)
        ''', ('admin', generate_password_hash(admin_pw), 'admin', 'System Administrator'))
        print(f"⚠️  SEED ADMIN PASSWORD: {admin_pw}")
        print("⚠️  (Set SEED_ADMIN_PASSWORD environment variable to use a custom password)")

    # Seed PM user
    cursor.execute("SELECT 1 FROM users WHERE username = 'pm_user'")
    if not cursor.fetchone():
        pm_pw = get_seed_password('pm_user')
        cursor.execute('''
        INSERT INTO users (username, password_hash, role, full_name)
        VALUES (%s, %s, %s, %s)
        ''', ('pm_user', generate_password_hash(pm_pw), 'pm', 'John Project Manager'))
        print(f"⚠️  SEED PM PASSWORD: {pm_pw}")
        print("⚠️  (Set SEED_PM_PASSWORD environment variable to use a custom password)")

    # Seed Executive user
    cursor.execute("SELECT 1 FROM users WHERE username = 'exec_user'")
    if not cursor.fetchone():
        exec_pw = get_seed_password('exec_user')
        cursor.execute('''
        INSERT INTO users (username, password_hash, role, full_name)
        VALUES (%s, %s, %s, %s)
        ''', ('exec_user', generate_password_hash(exec_pw), 'executive', 'Jane Executive'))
        print(f"⚠️  SEED EXECUTIVE PASSWORD: {exec_pw}")
        print("⚠️  (Set SEED_EXEC_PASSWORD environment variable to use a custom password)")

    # Seed Team user
    cursor.execute("SELECT 1 FROM users WHERE username = 'team_user'")
    if not cursor.fetchone():
        team_pw = get_seed_password('team_user')
        cursor.execute('''
        INSERT INTO users (username, password_hash, role, full_name)
        VALUES (%s, %s, %s, %s)
        ''', ('team_user', generate_password_hash(team_pw), 'team', 'Bob Team Member'))
        print(f"⚠️  SEED TEAM PASSWORD: {team_pw}")
        print("⚠️  (Set SEED_TEAM_PASSWORD environment variable to use a custom password)")

    conn.commit()
    conn.close()
    print("Neon PostgreSQL database initialized successfully!")
    print("Tables created: users, projects, baseline_schedule, activity_log, expenditure_log, project_assignments, audit_log, risks, task_outputs")
    print("Seed users: admin, pm_user, exec_user, team_user")
    print("\n⚠️  IMPORTANT: Change all seed passwords in production!")
    print("⚠️  Store passwords in environment variables or a secure vault.\n")

if __name__ == '__main__':
    init_db()
