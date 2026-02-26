import streamlit as st
from werkzeug.security import check_password_hash, generate_password_hash
from database import (
    get_user_by_username,
    create_user,
    create_session_token,
    get_valid_session,
    delete_session_token,
    cleanup_expired_sessions,
)
import secrets
from datetime import datetime, timedelta
import security
import audit

def init_session():
    if "user" not in st.session_state:
        st.session_state["user"] = None
    if "role" not in st.session_state:
        st.session_state["role"] = None

    cleanup_expired_sessions()

    # IMMEDIATELY strip token from URL if it accidentally appears
    if "token" in st.query_params:
        del st.query_params["token"]

    if not st.session_state.get("user"):
        # Use secure cookie retrieval with signature verification
        token = security.get_secure_cookie("auth_token")

        if token:
            user = get_valid_session(token)
            if user:
                st.session_state["user"] = {
                    "id": user["user_id"],
                    "username": user["username"],
                    "full_name": user["full_name"],
                    "role": user["role"],
                    "status": user["status"],
                    "token": token,
                }
                st.session_state["role"] = user["role"]
            else:
                # Token is invalid or tampered, flag for deletion
                security.delete_secure_cookie("auth_token")

def login(username, password):
    """
    Secure login with rate limiting and input validation.
    """
    # Validate input
    is_valid, error_msg = security.validate_username(username)
    if not is_valid:
        return False
    
    # Rate limiting check
    is_allowed, remaining = security.check_rate_limit(f"login_{username}")
    if not is_allowed:
        st.error(f"Too many login attempts. Please try again in {security.LOCKOUT_DURATION // 60} minutes.")
        return False
    
    user = get_user_by_username(username)
    if user and check_password_hash(user["password_hash"], password):
        # Successful login - generate secure token
        token = secrets.token_urlsafe(32)
        expire_date = datetime.now() + timedelta(days=7)
        expires_at = expire_date.strftime("%Y-%m-%d %H:%M:%S")
        create_session_token(user["user_id"], token, expires_at)

        st.session_state["user"] = {
            "id": user["user_id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"],
            "status": user["status"],
            "token": token,
        }
        st.session_state["role"] = user["role"]

        # Set secure cookie with proper flags
        security.set_secure_cookie("auth_token", token)
        
        # Reset rate limit on successful login
        security.reset_rate_limit(f"login_{username}")
        
        # AUDIT: Log successful login
        audit.log_audit(
            event_type="LOGIN",
            category="AUTH",
            description=f"User {username} logged in successfully",
            metadata={
                "username": username,
                "user_id": user["user_id"],
                "role": user["role"],
                "ip": audit.get_ip_address()
            },
            user_id=user["user_id"]
        )
        
        # Start session tracking
        audit.start_session_tracking()
        
        return True
    else:
        # Record failed attempt
        security.record_attempt(f"login_{username}")
        
        # AUDIT: Log failed login attempt
        audit.log_audit(
            event_type="LOGIN_FAILED",
            category="AUTH",
            description=f"Failed login attempt for user {username}",
            metadata={
                "username": username,
                "ip": audit.get_ip_address(),
                "remaining_attempts": remaining
            }
        )
        
        return False

def register(username, password, full_name, role="pm"):
    """
    Secure user registration with input validation.
    """
    # Validate username
    is_valid, error_msg = security.validate_username(username)
    if not is_valid:
        return False, error_msg
    
    # Validate password strength
    is_valid, error_msg = security.validate_password(password)
    if not is_valid:
        return False, error_msg
    
    # Validate full name
    if not full_name or len(full_name.strip()) < 2:
        return False, "Full name is required (minimum 2 characters)"
    
    if get_user_by_username(username):
        return False, "Username already exists"

    password_hash = generate_password_hash(password)
    create_user(
        {
            "username": username,
            "password_hash": password_hash,
            "full_name": full_name.strip(),
            "role": role,
            "status": "pending",
        }
    )
    return True, "User registered successfully. Access is pending Admin approval."

def logout():
    """Securely logout and clear all session data."""
    user = st.session_state.get("user", {})
    user_id = user.get("id")
    username = user.get("username")
    
    # AUDIT: Log logout and session duration BEFORE clearing session
    if user_id:
        audit.end_session_tracking()
        audit.log_audit(
            event_type="LOGOUT",
            category="AUTH",
            description=f"User {username} logged out",
            metadata={
                "username": username,
                "user_id": user_id
            },
            user_id=user_id
        )
    
    token = st.session_state.get("user", {}).get("token")
    if token:
        delete_session_token(token)

    st.session_state["user"] = None
    st.session_state["role"] = None

    # Securely delete the cookie
    security.delete_secure_cookie("auth_token")

    # Clear any URL tokens
    if "token" in st.query_params:
        del st.query_params["token"]

    st.rerun()

def is_logged_in():
    return st.session_state.get("user") is not None

def require_role(roles):
    if not is_logged_in():
        st.error("Please login to access this page")
        st.stop()

    user = get_current_user()
    if user.get("status") != "approved":
        st.error("Access Denied: Your account is pending administrator approval.")
        st.stop()

    user_role = st.session_state.get("role")
    if user_role not in roles and user_role != "admin":
        st.markdown(
            """
            <div style="background: rgba(239, 68, 68, 0.1); padding: 2rem; border-radius: 12px; border: 1px solid rgba(239, 68, 68, 0.3); text-align: center;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">🔒</div>
                <h2 style="color: #ef4444 !important; margin-bottom: 0.5rem;">Access Denied</h2>
                <div style="opacity: 0.8; margin-bottom: 2rem;">You do not have the required permissions to view this page.</div>
            </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button(
            "Return to Dashboard Home", use_container_width=True, type="primary"
        ):
            st.switch_page("main.py")
        st.stop()

def get_current_user():
    return st.session_state.get("user")
