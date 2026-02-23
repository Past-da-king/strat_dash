import sqlite3
import pandas as pd
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'pm_tool.db')
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), 'uploads')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def execute_query(query, params=(), commit=False):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit:
            conn.commit()
            return cursor.lastrowid
        return cursor.fetchall()

def get_df(query, params=()):
    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)

def log_change(table_name, record_id, action, old_val, new_val, user_id):
    query = '''
    INSERT INTO audit_log (table_name, record_id, action, old_value, new_value, changed_by)
    VALUES (?, ?, ?, ?, ?, ?)
    '''
    execute_query(query, (table_name, record_id, action, str(old_val), str(new_val), user_id), commit=True)

# ============================================================
# User Management
# ============================================================
def get_user_by_username(username):
    res = execute_query("SELECT * FROM users WHERE username = ?", (username,))
    return res[0] if res else None

def create_user(data):
    query = '''
    INSERT INTO users (username, password_hash, role, full_name, status)
    VALUES (?, ?, ?, ?, ?)
    '''
    params = (data['username'], data['password_hash'], data['role'], data['full_name'], data.get('status', 'approved'))
    return execute_query(query, params, commit=True)

def update_user_status(user_id, new_status):
    query = "UPDATE users SET status = ? WHERE user_id = ?"
    execute_query(query, (new_status, user_id), commit=True)

def update_user_role(user_id, new_role):
    query = "UPDATE users SET role = ? WHERE user_id = ?"
    execute_query(query, (new_role, user_id), commit=True)

def get_pending_users_count():
    res = execute_query("SELECT COUNT(*) as cnt FROM users WHERE status = 'pending'")
    return res[0]['cnt'] if res else 0

def get_all_users():
    return get_df("SELECT * FROM users")

def delete_user(user_id):
    execute_query("DELETE FROM project_assignments WHERE user_id = ?", (user_id,), commit=True)
    execute_query("DELETE FROM users WHERE user_id = ?", (user_id,), commit=True)

# ============================================================
# Project Assignment
# ============================================================
def assign_user_to_project(project_id, user_id, role, assigned_by):
    query = '''
    INSERT OR REPLACE INTO project_assignments (project_id, user_id, assigned_role, assigned_by)
    VALUES (?, ?, ?, ?)
    '''
    execute_query(query, (project_id, user_id, role, assigned_by), commit=True)

def remove_user_from_project(project_id, user_id):
    execute_query("DELETE FROM project_assignments WHERE project_id = ? AND user_id = ?", (project_id, user_id), commit=True)

def get_project_assignments(project_id):
    return get_df('''
        SELECT pa.*, u.full_name, u.username 
        FROM project_assignments pa
        JOIN users u ON pa.user_id = u.user_id
        WHERE pa.project_id = ?
    ''', (project_id,))

def get_project_users(project_id):
    """Return all users assigned to a project (for responsible person dropdowns)."""
    return get_df('''
        SELECT DISTINCT u.user_id, u.full_name, u.username, u.role
        FROM users u
        LEFT JOIN project_assignments pa ON u.user_id = pa.user_id AND pa.project_id = ?
        WHERE u.status = 'approved'
        ORDER BY u.full_name
    ''', (project_id,))

# ============================================================
# Project Management
# ============================================================
def create_project(data, user_id):
    query = '''
    INSERT INTO projects (project_name, project_number, client, pm_user_id, total_budget, start_date, target_end_date, created_by)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    '''
    params = (
        data['project_name'], data['project_number'], data.get('client'),
        data.get('pm_user_id'), data['total_budget'], data['start_date'],
        data['target_end_date'], user_id
    )
    project_id = execute_query(query, params, commit=True)
    log_change('projects', project_id, 'INSERT', None, data, user_id)
    return project_id

def update_project_pm(project_id, new_pm_id, changed_by):
    execute_query("UPDATE projects SET pm_user_id = ? WHERE project_id = ?", (new_pm_id, project_id), commit=True)
    execute_query("DELETE FROM project_assignments WHERE project_id = ? AND assigned_role = 'pm'", (project_id,), commit=True)
    assign_user_to_project(project_id, new_pm_id, 'pm', changed_by)

def get_projects(pm_id=None, user_id=None):
    if user_id:
        # Get projects where user is either the PM or explicitly assigned
        query = '''
        SELECT DISTINCT p.* 
        FROM projects p
        LEFT JOIN project_assignments pa ON p.project_id = pa.project_id
        LEFT JOIN baseline_schedule bs ON p.project_id = bs.project_id
        WHERE p.pm_user_id = ? 
           OR pa.user_id = ? 
           OR bs.responsible_user_id = ?
        '''
        return get_df(query, (user_id, user_id, user_id))
    elif pm_id:
        return get_df("SELECT * FROM projects WHERE pm_user_id = ?", (pm_id,))
    return get_df("SELECT * FROM projects")

# ============================================================
# Activity Management
# ============================================================
def update_activity_status(activity_id, new_status, user_id):
    """
    Updates activity status with dependency checks.
    """
    current_act = execute_query("SELECT * FROM baseline_schedule WHERE activity_id = ?", (activity_id,))
    if not current_act:
        return False, "Activity not found."
    
    current_act = current_act[0]
    dep_id = current_act['depends_on']
    
    if new_status in ['Active', 'Complete'] and dep_id:
        dep_act = execute_query("SELECT status FROM baseline_schedule WHERE activity_id = ?", (dep_id,))
        if dep_act and dep_act[0]['status'] != 'Complete':
            dep_name = execute_query("SELECT activity_name FROM baseline_schedule WHERE activity_id = ?", (dep_id,))[0]['activity_name']
            return False, f"Cannot progress. Predecessor '{dep_name}' must be 'Complete' first."

    query = "UPDATE baseline_schedule SET status = ? WHERE activity_id = ?"
    execute_query(query, (new_status, activity_id), commit=True)
    
    event_type = "STARTED" if new_status == "Active" else ("FINISHED" if new_status == "Complete" else "RESET")
    query_log = '''
    INSERT INTO activity_log (activity_id, event_type, event_date, recorded_by)
    VALUES (?, ?, date('now'), ?)
    '''
    execute_query(query_log, (activity_id, event_type, user_id), commit=True)
    
    return True, f"Status updated to {new_status}."

def update_activity_log(activity_id, event_type, event_date, user_id):
    query = '''
    INSERT INTO activity_log (activity_id, event_type, event_date, recorded_by)
    VALUES (?, ?, ?, ?)
    '''
    log_id = execute_query(query, (activity_id, event_type, event_date, user_id), commit=True)
    return log_id

# ============================================================
# Expenditure Management
# ============================================================
def add_expenditure(data, user_id):
    query = '''
    INSERT INTO expenditure_log (project_id, activity_id, category, description, reference_id, amount, spend_date, recorded_by)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    '''
    params = (
        data['project_id'], data.get('activity_id'), data['category'],
        data.get('description'), data['reference_id'], data['amount'],
        data['spend_date'], user_id
    )
    exp_id = execute_query(query, params, commit=True)
    return exp_id

# ============================================================
# Baseline Schedule (UPDATED: includes responsible_user_id, expected_output)
# ============================================================
def add_baseline_activity(data):
    query = '''
    INSERT INTO baseline_schedule (project_id, activity_name, planned_start, planned_finish, budgeted_cost, responsible_user_id, expected_output)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    '''
    params = (
        data['project_id'], data['activity_name'], data['planned_start'],
        data['planned_finish'], data['budgeted_cost'],
        data.get('responsible_user_id'), data.get('expected_output')
    )
    return execute_query(query, params, commit=True)

def get_baseline_schedule(project_id, user_id_filter=None):
    """Returns schedule with responsible person name joined. Optionally filter by responsible person."""
    query = '''
        SELECT bs.*, u.full_name as responsible_name
        FROM baseline_schedule bs
        LEFT JOIN users u ON bs.responsible_user_id = u.user_id
        WHERE bs.project_id = ?
    '''
    params = [project_id]
    
    if user_id_filter:
        query += " AND bs.responsible_user_id = ?"
        params.append(user_id_filter)
        
    query += " ORDER BY bs.planned_start"
    return get_df(query, tuple(params))

# ============================================================
# Risk Management
# ============================================================
def get_project_risks(project_id):
    return get_df("SELECT * FROM risks WHERE project_id = ? ORDER BY date_identified DESC", (project_id,))

def add_risk(data, user_id):
    query = '''
    INSERT INTO risks (project_id, date_identified, description, impact, status, mitigation_action, recorded_by)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    '''
    params = (
        data['project_id'], data.get('date_identified'), data['description'],
        data.get('impact'), data.get('status', 'Open'), data.get('mitigation_action'), user_id
    )
    return execute_query(query, params, commit=True)

def update_risk_status(risk_id, new_status, user_id):
    query = "UPDATE risks SET status = ?, recorded_by = ? WHERE risk_id = ?"
    return execute_query(query, (new_status, user_id, risk_id), commit=True)

# ============================================================
# Task Outputs (NEW)
# ============================================================
def save_task_output(activity_id, file_name, file_path, user_id):
    """Insert a completed output entry into task_outputs."""
    query = '''
    INSERT INTO task_outputs (activity_id, file_name, file_path, uploaded_by)
    VALUES (?, ?, ?, ?)
    '''
    return execute_query(query, (activity_id, file_name, file_path, user_id), commit=True)

def get_task_outputs(activity_id):
    """Fetch all outputs linked to a specific task."""
    return get_df('''
        SELECT to2.*, u.full_name as uploader_name
        FROM task_outputs to2
        JOIN users u ON to2.uploaded_by = u.user_id
        WHERE to2.activity_id = ?
        ORDER BY to2.uploaded_at DESC
    ''', (activity_id,))

def get_all_outputs_for_project(project_id):
    """Fetch all outputs across all tasks for a project (for dashboard)."""
    return get_df('''
        SELECT to2.*, bs.activity_name, u.full_name as uploader_name
        FROM task_outputs to2
        JOIN baseline_schedule bs ON to2.activity_id = bs.activity_id
        JOIN users u ON to2.uploaded_by = u.user_id
        WHERE bs.project_id = ?
        ORDER BY to2.uploaded_at DESC
    ''', (project_id,))
