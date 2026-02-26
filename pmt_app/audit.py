"""
Audit & Monitoring Module for Strat Edge Project Portal
Tracks: User activities, file operations, session duration, page views
"""

import streamlit as st
from datetime import datetime
import database
import hashlib
import socket


# =============================================================================
# AUDIT LOGGING
# =============================================================================

def get_user_fingerprint() -> str:
    """
    Generate a unique fingerprint for the current session/user.
    Combines IP, user agent, and session info.
    """
    try:
        # Get IP address
        ip = st.context.headers.get("X-Forwarded-For", 
                                    st.context.headers.get("X-Real-IP", 
                                    st.context.headers.get("Remote-Addr", "unknown")))
        
        # Get user agent
        user_agent = st.context.headers.get("User-Agent", "unknown")
        
        # Get session ID
        session_id = st.session_state.get("session_id", "unknown")
        
        # Create fingerprint
        fingerprint_data = f"{ip}|{user_agent}|{session_id}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
    except:
        return "unknown"


def get_ip_address() -> str:
    """Get the client IP address."""
    try:
        return st.context.headers.get("X-Forwarded-For", 
                                     st.context.headers.get("X-Real-IP", 
                                     st.context.headers.get("Remote-Addr", "unknown")))
    except:
        return "unknown"


def log_audit(event_type: str, category: str, description: str, 
              metadata: dict = None, user_id: int = None):
    """
    Log an audit event to the database.
    
    Args:
        event_type: Type of event (LOGIN, LOGOUT, VIEW, UPLOAD, DOWNLOAD, CREATE, UPDATE, DELETE)
        category: Category (AUTH, FILE, PROJECT, ACTIVITY, RISK, EXPENDITURE, NAVIGATION)
        description: Human-readable description
        metadata: Additional data as dict (will be stored as JSON string)
        user_id: User ID (defaults to current user)
    """
    try:
        if user_id is None:
            user = auth.get_current_user()
            user_id = user.get('id') if user else None
        
        # Get session info
        ip_address = get_ip_address()
        fingerprint = get_user_fingerprint()
        
        # Convert metadata to string
        metadata_str = str(metadata) if metadata else None
        
        # Insert audit log
        query = """
        INSERT INTO audit_logs 
        (user_id, event_type, category, description, ip_address, session_fingerprint, metadata, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        database.execute_query(query, (
            user_id,
            event_type,
            category,
            description,
            ip_address,
            fingerprint,
            metadata_str,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ), commit=True)
        
    except Exception as e:
        # Don't break the app if audit logging fails
        print(f"Audit logging failed: {e}")


# =============================================================================
# SESSION TRACKING
# =============================================================================

def start_session_tracking():
    """Initialize session tracking when user logs in."""
    if "_session_start" not in st.session_state:
        st.session_state["_session_start"] = datetime.now()
        st.session_state["_session_id"] = hashlib.sha256(
            f"{datetime.now()}|{st.session_state.get('user', {})}".encode()
        ).hexdigest()[:32]
        
        # Log session start
        log_audit(
            event_type="SESSION_START",
            category="AUTH",
            description=f"User session started",
            metadata={
                "session_id": st.session_state["_session_id"],
                "ip": get_ip_address(),
                "start_time": st.session_state["_session_start"].strftime('%Y-%m-%d %H:%M:%S')
            }
        )


def end_session_tracking():
    """Log session end and duration when user logs out."""
    if "_session_start" in st.session_state:
        start_time = st.session_state["_session_start"]
        end_time = datetime.now()
        duration = end_time - start_time
        duration_seconds = duration.total_seconds()
        session_id = st.session_state.get("_session_id", "unknown")
        
        # Format duration nicely
        hours, remainder = divmod(int(duration_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_formatted = f"{hours}h {minutes}m {seconds}s"
        
        # Log session end with EXACT duration
        log_audit(
            event_type="SESSION_END",
            category="AUTH",
            description=f"User session ended - Duration: {duration_formatted}",
            metadata={
                "session_id": session_id,
                "duration_seconds": duration_seconds,
                "duration_formatted": duration_formatted,
                "start_time": start_time.strftime('%Y-%m-%d %H:%M:%S'),
                "end_time": end_time.strftime('%Y-%m-%d %H:%M:%S')
            }
        )
        
        # Clear session tracking
        del st.session_state["_session_start"]


def track_page_view(page_name: str, page_path: str = None):
    """
    Track when a user views a page.
    
    Args:
        page_name: Human-readable page name
        page_path: Optional page path/file
    """
    user = auth.get_current_user()
    if not user:
        return
    
    log_audit(
        event_type="VIEW",
        category="NAVIGATION",
        description=f"User viewed {page_name}",
        metadata={
            "page_name": page_name,
            "page_path": page_path,
            "session_id": st.session_state.get("_session_id")
        }
    )


# =============================================================================
# FILE OPERATION TRACKING
# =============================================================================

def track_file_upload(file_name: str, file_size: int, file_type: str, 
                      location: str, project_id: int = None):
    """
    Track file upload events.
    
    Args:
        file_name: Name of uploaded file
        file_size: Size in bytes
        file_type: File extension/type
        location: Where it was uploaded (e.g., "repository", "activity", "risk")
        project_id: Optional project ID
    """
    log_audit(
        event_type="UPLOAD",
        category="FILE",
        description=f"Uploaded file: {file_name}",
        metadata={
            "file_name": file_name,
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "file_type": file_type,
            "location": location,
            "project_id": project_id,
            "session_id": st.session_state.get("_session_id")
        }
    )


def track_file_download(file_name: str, file_size: int, file_type: str,
                        location: str, file_id: int = None, project_id: int = None):
    """
    Track file download events.
    
    Args:
        file_name: Name of downloaded file
        file_size: Size in bytes
        file_type: File extension/type
        location: Where it was downloaded from
        file_id: Database ID of the file
        project_id: Optional project ID
    """
    log_audit(
        event_type="DOWNLOAD",
        category="FILE",
        description=f"Downloaded file: {file_name}",
        metadata={
            "file_name": file_name,
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "file_type": file_type,
            "location": location,
            "file_id": file_id,
            "project_id": project_id,
            "session_id": st.session_state.get("_session_id")
        }
    )


def track_file_delete(file_name: str, location: str, file_id: int = None):
    """
    Track file deletion events.
    
    Args:
        file_name: Name of deleted file
        location: Where it was deleted from
        file_id: Database ID of the file
    """
    log_audit(
        event_type="DELETE",
        category="FILE",
        description=f"Deleted file: {file_name}",
        metadata={
            "file_name": file_name,
            "location": location,
            "file_id": file_id,
            "session_id": st.session_state.get("_session_id")
        }
    )


# =============================================================================
# ACTION TRACKING
# =============================================================================

def track_action(action_type: str, category: str, target: str, 
                 target_id: int = None, metadata: dict = None):
    """
    Track user actions (CREATE, UPDATE, DELETE).
    
    Args:
        action_type: CREATE, UPDATE, or DELETE
        category: PROJECT, ACTIVITY, RISK, EXPENDITURE, USER
        target: What was acted upon
        target_id: Database ID of the target
        metadata: Additional context
    """
    log_audit(
        event_type=action_type,
        category=category,
        description=f"{action_type.capitalize()}d {target}",
        metadata={
            "target": target,
            "target_id": target_id,
            **(metadata or {})
        }
    )


# =============================================================================
# ANALYTICS QUERIES
# =============================================================================

def get_user_activity_summary(user_id: int = None, days: int = 30):
    """
    Get summary of user activity for the specified period.
    
    Args:
        user_id: Specific user ID or None for all users
        days: Number of days to look back
    
    Returns:
        DataFrame with activity summary
    """
    import pandas as pd
    
    date_filter = f"AND created_at >= datetime('now', '-{days} days')" if days else ""
    user_filter = f"WHERE user_id = {user_id}" if user_id else ""
    
    query = f"""
    SELECT 
        user_id,
        event_type,
        category,
        COUNT(*) as event_count,
        MIN(created_at) as first_event,
        MAX(created_at) as last_event
    FROM audit_logs
    {user_filter}
    {date_filter}
    GROUP BY user_id, event_type, category
    ORDER BY event_count DESC
    """
    
    return database.get_df(query)


def get_file_activity_summary(days: int = 30):
    """
    Get summary of file operations (uploads/downloads).
    
    Args:
        days: Number of days to look back
    
    Returns:
        DataFrame with file activity summary
    """
    import pandas as pd
    
    date_filter = f"AND created_at >= datetime('now', '-{days} days')" if days else ""
    
    query = f"""
    SELECT 
        event_type,
        COUNT(*) as count,
        SUM(CAST(JSON_EXTRACT(metadata, '$.file_size_bytes') AS INTEGER)) as total_bytes,
        AVG(CAST(JSON_EXTRACT(metadata, '$.file_size_bytes') AS INTEGER)) as avg_size
    FROM audit_logs
    WHERE category = 'FILE'
    {date_filter}
    GROUP BY event_type
    """
    
    return database.get_df(query)


def get_active_users(days: int = 7):
    """
    Get list of active users in the specified period.
    
    Args:
        days: Number of days to look back
    
    Returns:
        DataFrame with active users
    """
    import pandas as pd
    
    query = f"""
    SELECT 
        u.user_id,
        u.username,
        u.full_name,
        u.role,
        COUNT(DISTINCT al.session_fingerprint) as session_count,
        COUNT(*) as total_events,
        MIN(al.created_at) as first_activity,
        MAX(al.created_at) as last_activity
    FROM audit_logs al
    JOIN users u ON al.user_id = u.user_id
    WHERE al.created_at >= datetime('now', '-{days} days')
    GROUP BY u.user_id, u.username, u.full_name, u.role
    ORDER BY total_events DESC
    """
    
    return database.get_df(query)


def get_session_duration_summary(days: int = 30):
    """
    Get session duration statistics.
    
    Args:
        days: Number of days to look back
    
    Returns:
        DataFrame with session duration stats
    """
    import pandas as pd
    
    query = f"""
    SELECT 
        u.user_id,
        u.username,
        u.full_name,
        COUNT(*) as session_count,
        AVG(CAST(JSON_EXTRACT(al.metadata, '$.duration_seconds') AS FLOAT)) as avg_duration_seconds,
        MAX(CAST(JSON_EXTRACT(al.metadata, '$.duration_seconds') AS FLOAT)) as max_duration_seconds,
        SUM(CAST(JSON_EXTRACT(al.metadata, '$.duration_seconds') AS FLOAT)) as total_duration_seconds
    FROM audit_logs al
    JOIN users u ON al.user_id = u.user_id
    WHERE al.event_type = 'SESSION_END'
    AND al.created_at >= datetime('now', '-{days} days')
    GROUP BY u.user_id, u.username, u.full_name
    ORDER BY total_duration_seconds DESC
    """
    
    return database.get_df(query)


def get_recent_activity(limit: int = 100):
    """
    Get most recent audit log entries.
    
    Args:
        limit: Number of records to return
    
    Returns:
        DataFrame with recent activity
    """
    import pandas as pd
    
    query = f"""
    SELECT 
        al.*,
        u.username,
        u.full_name,
        u.role
    FROM audit_logs al
    LEFT JOIN users u ON al.user_id = u.user_id
    ORDER BY al.created_at DESC
    LIMIT {limit}
    """
    
    return database.get_df(query)


# Import auth at the end to avoid circular imports
import auth
