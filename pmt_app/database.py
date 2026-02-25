import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import streamlit as st
import os

UPLOADS_DIR = os.path.join(os.path.dirname(__file__), 'uploads')

import sqlite3
import pandas as pd
import streamlit as st
import os

# --- DATABASE TOGGLE ---
USE_LOCAL_SQLITE = True  # Set to False to switch back to Neon PostgreSQL
SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), 'pm_tool.db')
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), 'uploads')

def get_connection():
    """Create a connection to the local SQLite database."""
    conn = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # This makes results act like dictionaries
    return conn

def execute_query(query, params=(), commit=False):
    """Executes a query against the local SQLite database."""
    # Automatic placeholder conversion for compatibility
    query = query.replace('%s', '?')
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit:
            # For RETURNING-style queries in SQLite, we might need the ID
            last_id = cursor.lastrowid
            conn.commit()
            # Only clear cache if we are inside a Streamlit session
            try:
                st.cache_data.clear()
            except:
                pass 
            return last_id
        else:
            # IMPORTANT: Fetch all results immediately to avoid "statements in progress" errors
            results = [dict(row) for row in cursor.fetchall()]
            return results
    except Exception as e:
        if commit: conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

@st.cache_data(ttl=600)
def get_df(query, params=()):
    try:
        results = execute_query(query, params)
        return pd.DataFrame(results)
    except Exception as e:
        print(f"Error getting DataFrame: {e}")
        return pd.DataFrame()

def log_change(table_name, record_id, action, old_val, new_val, user_id):
    query = '''
    INSERT INTO audit_log (table_name, record_id, action, old_value, new_value, changed_by)
    VALUES (%s, %s, %s, %s, %s, %s)
    '''
    execute_query(query, (table_name, record_id, action, str(old_val), str(new_val), user_id), commit=True)

# ============================================================
# User Management
# ============================================================
def get_user_by_username(username):
    res = execute_query("SELECT * FROM users WHERE username = %s", (username,))
    return res[0] if res else None

def create_user(data):
    query = '''
    INSERT INTO users (username, password_hash, role, full_name, status)
    VALUES (%s, %s, %s, %s, %s) RETURNING user_id
    '''
    params = (data['username'], data['password_hash'], data['role'], data['full_name'], data.get('status', 'approved'))
    return execute_query(query, params, commit=True)

def update_user_status(user_id, new_status):
    query = "UPDATE users SET status = %s WHERE user_id = %s"
    execute_query(query, (new_status, user_id), commit=True)

def update_user_role(user_id, new_role):
    query = "UPDATE users SET role = %s WHERE user_id = %s"
    execute_query(query, (new_role, user_id), commit=True)

def get_pending_users_count():
    res = execute_query("SELECT COUNT(*) as cnt FROM users WHERE status = 'pending'")
    return res[0]['cnt'] if res else 0

def get_all_users():
    return get_df("SELECT * FROM users")

def delete_user(user_id):
    execute_query("DELETE FROM project_assignments WHERE user_id = %s", (user_id,), commit=True)
    execute_query("DELETE FROM users WHERE user_id = %s", (user_id,), commit=True)

# ============================================================
# Project Assignment
# ============================================================
def assign_user_to_project(project_id, user_id, role, assigned_by):
    query = '''
    INSERT INTO project_assignments (project_id, user_id, assigned_role, assigned_by)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (project_id, user_id) DO UPDATE SET assigned_role = EXCLUDED.assigned_role, assigned_by = EXCLUDED.assigned_by
    '''
    execute_query(query, (project_id, user_id, role, assigned_by), commit=True)

def remove_user_from_project(project_id, user_id):
    execute_query("DELETE FROM project_assignments WHERE project_id = %s AND user_id = %s", (project_id, user_id), commit=True)

def get_project_assignments(project_id):
    return get_df('''
        SELECT pa.*, u.full_name, u.username 
        FROM project_assignments pa
        JOIN users u ON pa.user_id = u.user_id
        WHERE pa.project_id = %s
    ''', (project_id,))

def get_project_users(project_id):
    """Return all users assigned to a project (for responsible person dropdowns)."""
    return get_df('''
        SELECT DISTINCT u.user_id, u.full_name, u.username, u.role
        FROM users u
        LEFT JOIN project_assignments pa ON u.user_id = pa.user_id AND pa.project_id = %s
        WHERE u.status = 'approved'
        ORDER BY u.full_name
    ''', (project_id,))

# ============================================================
# Project Management
# ============================================================
def create_project(data, user_id):
    query = '''
    INSERT INTO projects (project_name, project_number, client, pm_user_id, total_budget, start_date, target_end_date, created_by)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING project_id
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
    execute_query("UPDATE projects SET pm_user_id = %s WHERE project_id = %s", (new_pm_id, project_id), commit=True)
    execute_query("DELETE FROM project_assignments WHERE project_id = %s AND assigned_role = 'pm'", (project_id,), commit=True)
    assign_user_to_project(project_id, new_pm_id, 'pm', changed_by)

def get_projects(pm_id=None, user_id=None):
    if user_id:
        # Optimized query with EXISTS for better performance
        query = '''
        SELECT p.* 
        FROM projects p
        WHERE p.pm_user_id = %s 
           OR EXISTS (SELECT 1 FROM project_assignments pa WHERE pa.project_id = p.project_id AND pa.user_id = %s)
           OR EXISTS (SELECT 1 FROM baseline_schedule bs WHERE bs.project_id = p.project_id AND bs.responsible_user_id = %s)
        '''
        return get_df(query, (user_id, user_id, user_id))
    elif pm_id:
        return get_df("SELECT * FROM projects WHERE pm_user_id = %s", (pm_id,))
    return get_df("SELECT * FROM projects")

# ============================================================
# Activity Management
# ============================================================
def update_activity_status(activity_id, new_status, user_id):
    """
    Updates activity status with dependency checks.
    """
    current_act = execute_query("SELECT * FROM baseline_schedule WHERE activity_id = %s", (activity_id,))
    if not current_act:
        return False, "Activity not found."
    
    current_act = current_act[0]
    dep_id = current_act['depends_on']
    
    if new_status in ['Active', 'Complete'] and dep_id:
        dep_act = execute_query("SELECT status FROM baseline_schedule WHERE activity_id = %s", (dep_id,))
        if dep_act and dep_act[0]['status'] != 'Complete':
            dep_name = execute_query("SELECT activity_name FROM baseline_schedule WHERE activity_id = %s", (dep_id,))[0]['activity_name']
            return False, f"Cannot progress. Predecessor '{dep_name}' must be 'Complete' first."

    query = "UPDATE baseline_schedule SET status = %s WHERE activity_id = %s"
    execute_query(query, (new_status, activity_id), commit=True)
    
    event_type = "STARTED" if new_status == "Active" else ("FINISHED" if new_status == "Complete" else "RESET")
    query_log = '''
    INSERT INTO activity_log (activity_id, event_type, event_date, recorded_by)
    VALUES (%s, %s, CURRENT_DATE, %s)
    '''
    execute_query(query_log, (activity_id, event_type, user_id), commit=True)
    
    return True, f"Status updated to {new_status}."

def update_activity_log(activity_id, event_type, event_date, user_id):
    query = '''
    INSERT INTO activity_log (activity_id, event_type, event_date, recorded_by)
    VALUES (%s, %s, %s, %s) RETURNING log_id
    '''
    log_id = execute_query(query, (activity_id, event_type, event_date, user_id), commit=True)
    return log_id

# ============================================================
# Expenditure Management
# ============================================================
def add_expenditure(data, user_id):
    query = '''
    INSERT INTO expenditure_log (project_id, activity_id, category, description, reference_id, amount, spend_date, recorded_by)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING exp_id
    '''
    params = (
        data['project_id'], data.get('activity_id'), data['category'],
        data.get('description'), data['reference_id'], data['amount'],
        data['spend_date'], user_id
    )
    exp_id = execute_query(query, params, commit=True)
    return exp_id

# ============================================================
# Baseline Schedule
# ============================================================
def add_baseline_activity(data):
    query = '''
    INSERT INTO baseline_schedule (project_id, activity_name, planned_start, planned_finish, budgeted_cost, responsible_user_id, expected_output)
    VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING activity_id
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
        WHERE bs.project_id = %s
    '''
    params = [project_id]
    
    if user_id_filter:
        query += " AND bs.responsible_user_id = %s"
        params.append(user_id_filter)
        
    query += " ORDER BY bs.planned_start"
    return get_df(query, tuple(params))

# ============================================================
# Risk Management
# ============================================================
def get_project_risks(project_id):
    query = '''
        SELECT r.*, bs.activity_name, u.full_name as responsible_name
        FROM risks r
        LEFT JOIN baseline_schedule bs ON r.activity_id = bs.activity_id
        LEFT JOIN users u ON bs.responsible_user_id = u.user_id
        WHERE r.project_id = %s
        ORDER BY r.date_identified DESC
    '''
    return get_df(query, (project_id,))

def add_risk(data, user_id):
    query = '''
    INSERT INTO risks (project_id, activity_id, date_identified, description, impact, status, mitigation_action, recorded_by)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING risk_id
    '''
    params = (
        data['project_id'], data.get('activity_id'), data.get('date_identified'), data['description'],
        data.get('impact'), data.get('status', 'Open'), data.get('mitigation_action'), user_id
    )
    return execute_query(query, params, commit=True)

def update_risk_status(risk_id, new_status, user_id, closure_file_path=None):
    query = "UPDATE risks SET status = %s, recorded_by = %s, closure_file_path = %s WHERE risk_id = %s"
    return execute_query(query, (new_status, user_id, closure_file_path, risk_id), commit=True)

# ============================================================
# Task Outputs
# ============================================================
def save_task_output(activity_id, file_name, file_path, user_id, doc_type='Regular Draft'):
    """Insert a completed output entry into task_outputs."""
    query = '''
    INSERT INTO task_outputs (activity_id, file_name, file_path, doc_type, uploaded_by)
    VALUES (%s, %s, %s, %s, %s) RETURNING output_id
    '''
    return execute_query(query, (activity_id, file_name, file_path, doc_type, user_id), commit=True)

def check_task_document_presence(activity_id, doc_type):
    """Check if a specific type of document has been uploaded for a task."""
    res = execute_query("SELECT COUNT(*) as cnt FROM task_outputs WHERE activity_id = %s AND doc_type = %s", (activity_id, doc_type))
    return res[0]['cnt'] > 0 if res else False

def get_task_outputs(activity_id):
    """Fetch all outputs linked to a specific task."""
    return get_df('''
        SELECT to2.*, u.full_name as uploader_name
        FROM task_outputs to2
        JOIN users u ON to2.uploaded_by = u.user_id
        WHERE to2.activity_id = %s
        ORDER BY to2.uploaded_at DESC
    ''', (activity_id,))

def get_all_outputs_for_project(project_id):
    """Fetch all outputs across all tasks for a project (for dashboard)."""
    return get_df('''
        SELECT to2.*, bs.activity_name, u.full_name as uploader_name
        FROM task_outputs to2
        JOIN baseline_schedule bs ON to2.activity_id = bs.activity_id
        JOIN users u ON to2.uploaded_by = u.user_id
        WHERE bs.project_id = %s
        ORDER BY to2.uploaded_at DESC
    ''', (project_id,))

def has_open_risks(activity_id):
    """Check if there are any open risks linked to this activity."""
    res = execute_query("SELECT COUNT(*) as cnt FROM risks WHERE activity_id = %s AND status = 'Open'", (activity_id,))
    return res[0]['cnt'] > 0 if res else False
