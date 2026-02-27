import streamlit as st
import pandas as pd
import os
import re
import security
import time
from azure.storage.blob import BlobServiceClient

# --- DATABASE CONFIG ---
SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), "pm_tool.db")
UPLOADS_DIR = None  # All file storage is now handled by Azure Blob Storage

# --- AZURE STORAGE CONFIG ---
AZURE_CONNECTION = st.secrets["azure"]["connection_string"]
AZURE_CONTAINER = st.secrets["azure"]["container_name"]

# --- FILE UPLOAD SECURITY SETTINGS ---
MAX_FILE_SIZE = security.MAX_FILE_SIZE  # 50 MB
ALLOWED_EXTENSIONS = set(security.ALLOWED_FILE_TYPES.keys())

def get_blob_client(blob_name):
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION)
    return blob_service_client.get_blob_client(container=AZURE_CONTAINER, blob=blob_name)

def upload_file_to_azure(file_bytes, blob_name, validate=True):
    """
    Uploads bytes to Azure Blob Storage with security validation.
    
    Args:
        file_bytes: File content in bytes
        blob_name: Destination blob name
        validate: Whether to perform security validation (default True)
    
    Returns:
        blob_name if successful
    
    Raises:
        ValueError: If file fails security validation
    """
    # Security validation
    if validate:
        # Check file size
        if len(file_bytes) > MAX_FILE_SIZE:
            raise ValueError(f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB")
        
        # Validate blob name to prevent path traversal
        if not _is_safe_blob_name(blob_name):
            raise ValueError("Invalid file name or path")
    
    blob_client = get_blob_client(blob_name)
    blob_client.upload_blob(file_bytes, overwrite=True)
    return blob_name


def _is_safe_blob_name(blob_name: str) -> bool:
    """
    Validate blob name to prevent path traversal and injection attacks.
    
    Checks:
    - No null bytes
    - No path traversal sequences (..)
    - Only allowed characters
    - Reasonable length
    """
    if not blob_name:
        return False
    
    # Check for null bytes
    if '\x00' in blob_name:
        return False
    
    # Check for path traversal
    if '..' in blob_name:
        return False
    
    # Check length (max 256 chars for Azure Blob)
    if len(blob_name) > 256:
        return False
    
    # Check for allowed characters (alphanumeric, /, -, _, ., and spaces)
    if not re.match(r'^[a-zA-Z0-9/\-_. ]+$', blob_name):
        return False
    
    return True

def download_file_from_azure(blob_name):
    """Downloads blob content as bytes."""
    blob_client = get_blob_client(blob_name)
    return blob_client.download_blob().readall()

def blob_exists(blob_name):
    """Checks if a blob exists in Azure."""
    blob_client = get_blob_client(blob_name)
    return blob_client.exists()

import sqlite3


def get_connection():
    conn = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_session_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS session_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    conn.commit()
    conn.close()


init_session_table()


def init_repository_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repository_files (
            file_id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            parent_id INTEGER,
            name TEXT NOT NULL,
            is_folder INTEGER NOT NULL DEFAULT 0,
            file_path TEXT,
            uploaded_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (project_id),
            FOREIGN KEY (parent_id) REFERENCES repository_files (file_id),
            FOREIGN KEY (uploaded_by) REFERENCES users (user_id)
        )
    """)
    conn.commit()
    conn.close()


init_repository_table()


def init_repository_links_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repository_links (
            link_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL, -- 'R' repo, 'A' activity, 'K' risk
            source_id INTEGER NOT NULL,
            target_type TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            created_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (user_id)
        )
    """)
    conn.commit()
    conn.close()


init_repository_links_table()


def init_audit_logs_table():
    """Initialize audit logs table for comprehensive activity tracking."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            audit_log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            event_type TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            ip_address TEXT,
            session_fingerprint TEXT,
            metadata TEXT,
            execution_time_ms INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    
    # Migration: Add execution_time_ms if it doesn't exist (for existing databases)
    try:
        cursor.execute("ALTER TABLE audit_logs ADD COLUMN execution_time_ms INTEGER")
    except sqlite3.OperationalError:
        # Column likely already exists
        pass

    # Create indexes for better query performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_logs(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_logs(event_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_category ON audit_logs(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_logs(session_fingerprint)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_exec_time ON audit_logs(execution_time_ms)")
    conn.commit()
    conn.close()


init_audit_logs_table()


def execute_query(query, params=(), commit=False, log_it=True):
    """
    Executes a query with automatic PostgreSQL-to-SQLite translation.
    
    SECURITY: All queries MUST use parameterized queries with %s placeholders.
    Never use string formatting or concatenation with user input.
    
    Args:
        query: SQL query with %s placeholders
        params: Tuple of parameters to bind
        commit: Whether to commit the transaction
        log_it: Whether to log performance to audit_logs
    
    Returns:
        Query results or last inserted ID
    
    Raises:
        ValueError: If query contains potential SQL injection patterns
    """
    # Security: Block dangerous patterns ONLY in user input context
    
    query_upper = query.upper()
    
    # Block SQL comment injection
    if '--' in query and 'CREATE ' not in query_upper and 'INSERT ' not in query_upper:
        raise ValueError("Potentially dangerous SQL comment detected")
    
    # Block multiple statement execution
    if query.count(';') > 1:
        raise ValueError("Multiple SQL statements detected")
    
    # Block dangerous patterns
    dangerous_patterns = ['XP_', 'SP_']
    for pattern in dangerous_patterns:
        if pattern in query_upper:
            raise ValueError(f"Potentially dangerous SQL pattern detected: {pattern}")
    
    # 1. Translate placeholders: %s -> ?
    query_processed = query.replace("%s", "?")

    # 2. SQLite Compatibility: Remove 'RETURNING ...' clauses
    query_processed = re.sub(r"\s+RETURNING\s+\w+", "", query_processed, flags=re.IGNORECASE)

    start_time = time.time()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query_processed, params)

        if commit:
            result = cursor.lastrowid
            conn.commit()
            try:
                st.cache_data.clear()
            except:
                pass
        else:
            result = [dict(row) for row in cursor.fetchall()]
        
        exec_time_ms = int((time.time() - start_time) * 1000)
        
        # Log performance (avoid recursion)
        if log_it and "audit_logs" not in query.lower():
            try:
                import audit
                audit.log_audit(
                    event_type="SQL_QUERY",
                    category="DATABASE",
                    description=f"SQL Executed ({query[:50]}...)",
                    metadata={"query": query, "params": str(params)},
                    execution_time_ms=exec_time_ms
                )
            except:
                pass
                
        return result
    except Exception as e:
        if commit:
            conn.rollback()
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
    query = """
    INSERT INTO audit_logs (event_type, category, description, metadata, user_id)
    VALUES (%s, %s, %s, %s, %s)
    """
    execute_query(
        query,
        (
            action, 
            "DATA_CHANGE", 
            f"Change in {table_name} (ID: {record_id})", 
            str({"table": table_name, "id": record_id, "old": old_val, "new": new_val}), 
            user_id
        ),
        commit=True,
    )


# ============================================================
# User Management
# ============================================================
def get_user_by_username(username):
    res = execute_query("SELECT * FROM users WHERE username = %s", (username,))
    return res[0] if res else None


def create_user(data):
    query = """
    INSERT INTO users (username, password_hash, role, full_name, status)
    VALUES (%s, %s, %s, %s, %s)
    """
    params = (
        data["username"],
        data["password_hash"],
        data["role"],
        data["full_name"],
        data.get("status", "approved"),
    )
    return execute_query(query, params, commit=True)


def update_user_status(user_id, new_status):
    query = "UPDATE users SET status = %s WHERE user_id = %s"
    execute_query(query, (new_status, user_id), commit=True)


def update_user_role(user_id, new_role):
    query = "UPDATE users SET role = %s WHERE user_id = %s"
    execute_query(query, (new_role, user_id), commit=True)


def get_pending_users_count():
    res = execute_query("SELECT COUNT(*) as cnt FROM users WHERE status = 'pending'")
    return res[0]["cnt"] if res else 0


def get_all_users():
    return get_df("SELECT * FROM users")


def delete_user(user_id):
    execute_query(
        "DELETE FROM project_assignments WHERE user_id = %s", (user_id,), commit=True
    )
    execute_query("DELETE FROM users WHERE user_id = %s", (user_id,), commit=True)


# ============================================================
# Project Assignment
# ============================================================
def assign_user_to_project(project_id, user_id, role, assigned_by):
    query = """
    INSERT INTO project_assignments (project_id, user_id, assigned_role, assigned_by)
    VALUES (%s, %s, %s, %s)
    """
    # SQLite doesn't support the complex ON CONFLICT ... DO UPDATE in one line as easily
    # Check if exists first
    existing = execute_query(
        "SELECT 1 FROM project_assignments WHERE project_id = %s AND user_id = %s",
        (project_id, user_id),
    )
    if existing:
        execute_query(
            "UPDATE project_assignments SET assigned_role = %s, assigned_by = %s WHERE project_id = %s AND user_id = %s",
            (role, assigned_by, project_id, user_id),
            commit=True,
        )
    else:
        execute_query(query, (project_id, user_id, role, assigned_by), commit=True)


def remove_user_from_project(project_id, user_id):
    execute_query(
        "DELETE FROM project_assignments WHERE project_id = %s AND user_id = %s",
        (project_id, user_id),
        commit=True,
    )


def get_project_assignments(project_id):
    return get_df(
        """
        SELECT pa.*, u.full_name, u.username 
        FROM project_assignments pa
        JOIN users u ON pa.user_id = u.user_id
        WHERE pa.project_id = %s
    """,
        (project_id,),
    )


def get_project_users(project_id):
    """Return all users assigned to a project (for responsible person dropdowns)."""
    return get_df(
        """
        SELECT DISTINCT u.user_id, u.full_name, u.username, u.role
        FROM users u
        LEFT JOIN project_assignments pa ON u.user_id = pa.user_id AND pa.project_id = %s
        WHERE u.status = 'approved'
        ORDER BY u.full_name
    """,
        (project_id,),
    )


# ============================================================
# Project Management
# ============================================================
def create_project(data, user_id):
    query = """
    INSERT INTO projects (project_name, project_number, client, pm_user_id, total_budget, start_date, target_end_date, created_by)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        data["project_name"],
        data["project_number"],
        data.get("client"),
        data.get("pm_user_id"),
        data["total_budget"],
        data["start_date"],
        data["target_end_date"],
        user_id,
    )
    project_id = execute_query(query, params, commit=True)
    log_change("projects", project_id, "INSERT", None, data, user_id)
    return project_id


def update_project_pm(project_id, new_pm_id, changed_by):
    execute_query(
        "UPDATE projects SET pm_user_id = %s WHERE project_id = %s",
        (new_pm_id, project_id),
        commit=True,
    )
    execute_query(
        "DELETE FROM project_assignments WHERE project_id = %s AND assigned_role = 'pm'",
        (project_id,),
        commit=True,
    )
    assign_user_to_project(project_id, new_pm_id, "pm", changed_by)


def get_projects(pm_id=None, user_id=None):
    if user_id:
        # Optimized query with EXISTS for better performance
        query = """
        SELECT p.* 
        FROM projects p
        WHERE p.pm_user_id = %s 
           OR EXISTS (SELECT 1 FROM project_assignments pa WHERE pa.project_id = p.project_id AND pa.user_id = %s)
           OR EXISTS (SELECT 1 FROM baseline_schedule bs WHERE bs.project_id = p.project_id AND bs.responsible_user_id = %s)
        """
        return get_df(query, (user_id, user_id, user_id))
    elif pm_id:
        return get_df("SELECT * FROM projects WHERE pm_user_id = %s", (pm_id,))
    return get_df("SELECT * FROM projects")


# ============================================================
# Activity Management
# ============================================================
def update_activity_status(activity_id, new_status, user_id):
    """
    Updates activity status.
    """
    current_act = execute_query(
        "SELECT * FROM baseline_schedule WHERE activity_id = %s", (activity_id,)
    )
    if not current_act:
        return False, "Activity not found."

    query = "UPDATE baseline_schedule SET status = %s WHERE activity_id = %s"
    execute_query(query, (new_status, activity_id), commit=True)

    event_type = (
        "STARTED"
        if new_status == "Active"
        else ("FINISHED" if new_status == "Complete" else "RESET")
    )
    query_log = """
    INSERT INTO activity_log (activity_id, event_type, event_date, recorded_by)
    VALUES (%s, %s, CURRENT_DATE, %s)
    """
    execute_query(query_log, (activity_id, event_type, user_id), commit=True)

    return True, f"Status updated to {new_status}."


def update_activity_log(activity_id, event_type, event_date, user_id):
    query = """
    INSERT INTO activity_log (activity_id, event_type, event_date, recorded_by)
    VALUES (%s, %s, %s, %s)
    """
    log_id = execute_query(
        query, (activity_id, event_type, event_date, user_id), commit=True
    )
    return log_id


# ============================================================
# Expenditure Management
# ============================================================
def add_expenditure(data, user_id):
    query = """
    INSERT INTO expenditure_log (project_id, activity_id, category, description, reference_id, amount, spend_date, recorded_by)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        data["project_id"],
        data.get("activity_id"),
        data["category"],
        data.get("description"),
        data["reference_id"],
        data["amount"],
        data["spend_date"],
        user_id,
    )
    exp_id = execute_query(query, params, commit=True)
    return exp_id


# ============================================================
# Baseline Schedule
# ============================================================
def add_baseline_activity(data):
    query = """
    INSERT INTO baseline_schedule (project_id, activity_name, planned_start, planned_finish, budgeted_cost, responsible_user_id, expected_output, depends_on)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        data["project_id"],
        data["activity_name"],
        data["planned_start"],
        data["planned_finish"],
        data["budgeted_cost"],
        data.get("responsible_user_id"),
        data.get("expected_output"),
        data.get("depends_on")
    )
    return execute_query(query, params, commit=True)


def update_baseline_activity(activity_id, data):
    """Surgically update an existing activity."""
    query = """
    UPDATE baseline_schedule 
    SET activity_name = %s, planned_start = %s, planned_finish = %s, 
        budgeted_cost = %s, responsible_user_id = %s, expected_output = %s, 
        depends_on = %s, status = %s
    WHERE activity_id = %s
    """
    params = (
        data["activity_name"],
        data["planned_start"],
        data["planned_finish"],
        data["budgeted_cost"],
        data.get("responsible_user_id"),
        data.get("expected_output"),
        data.get("depends_on"),
        data.get("status", "Not Started"),
        activity_id
    )
    execute_query(query, params, commit=True)


def delete_baseline_activity(activity_id):
    """Delete an activity and clear dependencies pointing to it."""
    execute_query("UPDATE baseline_schedule SET depends_on = NULL WHERE depends_on = %s", (activity_id,), commit=True)
    execute_query("DELETE FROM baseline_schedule WHERE activity_id = %s", (activity_id,), commit=True)


def get_baseline_schedule(project_id, user_id_filter=None):
    """Returns schedule with responsible person name joined. Optionally filter by responsible person."""
    query = """
        SELECT bs.*, u.full_name as responsible_name
        FROM baseline_schedule bs
        LEFT JOIN users u ON bs.responsible_user_id = u.user_id
        WHERE bs.project_id = %s
    """
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
    query = """
        SELECT r.*, bs.activity_name, u.full_name as responsible_name
        FROM risks r
        LEFT JOIN baseline_schedule bs ON r.activity_id = bs.activity_id
        LEFT JOIN users u ON bs.responsible_user_id = u.user_id
        WHERE r.project_id = %s
        ORDER BY r.date_identified DESC
    """
    return get_df(query, (project_id,))


def add_risk(data, user_id):
    query = """
    INSERT INTO risks (project_id, activity_id, date_identified, description, impact, status, mitigation_action, recorded_by)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        data["project_id"],
        data.get("activity_id"),
        data.get("date_identified"),
        data["description"],
        data.get("impact"),
        data.get("status", "Open"),
        data.get("mitigation_action"),
        user_id,
    )
    return execute_query(query, params, commit=True)


def update_risk_status(risk_id, new_status, user_id, closure_file_path=None):
    query = "UPDATE risks SET status = %s, recorded_by = %s, closure_file_path = %s WHERE risk_id = %s"
    return execute_query(
        query, (new_status, user_id, closure_file_path, risk_id), commit=True
    )


# ============================================================
# Task Outputs
# ============================================================
def save_task_output(
    activity_id, file_name, file_path, user_id, doc_type="Regular Draft"
):
    """Insert a completed output entry into task_outputs."""
    query = """
    INSERT INTO task_outputs (activity_id, file_name, file_path, doc_type, uploaded_by)
    VALUES (%s, %s, %s, %s, %s)
    """
    return execute_query(
        query, (activity_id, file_name, file_path, doc_type, user_id), commit=True
    )


def check_task_document_presence(activity_id, doc_type):
    """Check if a specific type of document has been uploaded for a task."""
    res = execute_query(
        "SELECT COUNT(*) as cnt FROM task_outputs WHERE activity_id = %s AND doc_type = %s",
        (activity_id, doc_type),
    )
    return res[0]["cnt"] > 0 if res else False


def get_task_outputs(activity_id):
    """Fetch all outputs linked to a specific task."""
    return get_df(
        """
        SELECT to2.*, u.full_name as uploader_name
        FROM task_outputs to2
        JOIN users u ON to2.uploaded_by = u.user_id
        WHERE to2.activity_id = %s
        ORDER BY to2.uploaded_at DESC
    """,
        (activity_id,),
    )


def get_all_outputs_for_project(project_id):
    """Fetch all outputs across all tasks for a project (for dashboard)."""
    return get_df(
        """
        SELECT to2.*, bs.activity_name, u.full_name as uploader_name
        FROM task_outputs to2
        JOIN baseline_schedule bs ON to2.activity_id = bs.activity_id
        JOIN users u ON to2.uploaded_by = u.user_id
        WHERE bs.project_id = %s
        ORDER BY to2.uploaded_at DESC
    """,
        (project_id,),
    )


def has_open_risks(activity_id):
    """Check if there are any open risks linked to this activity."""
    res = execute_query(
        "SELECT COUNT(*) as cnt FROM risks WHERE activity_id = %s AND status = 'Open'",
        (activity_id,),
    )
    return res[0]["cnt"] > 0 if res else False


# ============================================================
# Project Repository
# ============================================================
def create_repo_folder(project_id, name, parent_id, user_id):
    """Create a folder in the project repository."""
    query = """
    INSERT INTO repository_files (project_id, parent_id, name, is_folder, uploaded_by)
    VALUES (%s, %s, %s, 1, %s)
    """
    return execute_query(query, (project_id, parent_id, name, user_id), commit=True)


def add_repo_file(project_id, parent_id, name, file_path, user_id):
    """Add a file entry to the project repository."""
    query = """
    INSERT INTO repository_files (project_id, parent_id, name, is_folder, file_path, uploaded_by)
    VALUES (%s, %s, %s, 0, %s, %s)
    """
    return execute_query(query, (project_id, parent_id, name, file_path, user_id), commit=True)


def get_repo_contents(project_id, parent_id=None):
    """Get all items (folders and files) inside a given parent folder. Use parent_id=None for root."""
    if parent_id is None:
        query = """
            SELECT rf.*, u.full_name as uploader_name
            FROM repository_files rf
            LEFT JOIN users u ON rf.uploaded_by = u.user_id
            WHERE rf.project_id = %s AND rf.parent_id IS NULL
            ORDER BY rf.is_folder DESC, rf.name ASC
        """
        return get_df(query, (project_id,))
    else:
        query = """
            SELECT rf.*, u.full_name as uploader_name
            FROM repository_files rf
            LEFT JOIN users u ON rf.uploaded_by = u.user_id
            WHERE rf.project_id = %s AND rf.parent_id = %s
            ORDER BY rf.is_folder DESC, rf.name ASC
        """
        return get_df(query, (project_id, parent_id))


def delete_repo_item(file_id):
    """Delete a repository item (file or folder). For folders, children must be deleted first."""
    # Delete children first (recursive cleanup)
    children = execute_query("SELECT file_id FROM repository_files WHERE parent_id = %s", (file_id,))
    for child in children:
        delete_repo_item(child['file_id'])
    execute_query("DELETE FROM repository_files WHERE file_id = %s", (file_id,), commit=True)


def delete_task_output(output_id):
    """Delete a task output entry."""
    return execute_query("DELETE FROM task_outputs WHERE output_id = %s", (output_id,), commit=True)


def remove_risk_closure_file(risk_id, file_path):
    """Remove a specific closure file from a risk (handling comma-separated paths)."""
    res = execute_query("SELECT closure_file_path FROM risks WHERE risk_id = %s", (risk_id,))
    if not res:
        return False

    current_paths = res[0]["closure_file_path"]
    if not current_paths:
        return True

    path_list = [p.strip() for p in current_paths.split(",") if p.strip()]
    if file_path in path_list:
        path_list.remove(file_path)

    new_paths = ",".join(path_list) if path_list else None
    return execute_query(
        "UPDATE risks SET closure_file_path = %s WHERE risk_id = %s",
        (new_paths, risk_id),
        commit=True,
    )


def create_file_link(source_type, source_id, target_type, target_id, user_id):
    """Create a manual bi-directional link between two files or folders."""
    # To keep it bi-directional we just store it once and query both ways
    query = """
    INSERT INTO repository_links (source_type, source_id, target_type, target_id, created_by)
    VALUES (%s, %s, %s, %s, %s)
    """
    return execute_query(query, (source_type, source_id, target_type, target_id, user_id), commit=True)


def get_file_links(item_type, item_id):
    """Retrieve all items linked to this specific item (manually)."""
    # Fetch where it is source or where it is target
    query = """
    SELECT * FROM repository_links 
    WHERE (source_type = %s AND source_id = %s)
    OR (target_type = %s AND target_id = %s)
    """
    return execute_query(query, (item_type, item_id, item_type, item_id))


def delete_file_link(link_id):
    execute_query("DELETE FROM repository_links WHERE link_id = %s", (link_id,), commit=True)


def create_session_token(user_id, token, expires_at):
    query = """
    INSERT INTO session_tokens (user_id, token, expires_at)
    VALUES (%s, %s, %s)
    """
    execute_query(query, (user_id, token, expires_at), commit=True)


def get_valid_session(token):
    res = execute_query(
        """
        SELECT u.user_id, u.username, u.full_name, u.role, u.status
        FROM session_tokens st
        JOIN users u ON st.user_id = u.user_id
        WHERE st.token = %s AND st.expires_at > datetime('now')
    """,
        (token,),
    )
    return res[0] if res else None


def delete_session_token(token):
    execute_query("DELETE FROM session_tokens WHERE token = %s", (token,), commit=True)


def cleanup_expired_sessions():
    execute_query(
        "DELETE FROM session_tokens WHERE expires_at < datetime('now')", commit=True
    )
