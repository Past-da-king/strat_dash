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
        # Synchronously read the cookie natively from Streamlit
        token = st.context.cookies.get("auth_token")
        
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
                # Token is invalid, flag for deletion on front-end
                st.session_state["_del_cookie"] = True

def login(username, password):
    user = get_user_by_username(username)
    if user and check_password_hash(user["password_hash"], password):
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
        
        # Flag token to be written in the main layout frame so it resolves
        st.session_state["_set_cookie"] = token
        return True
    return False

def register(username, password, full_name, role="pm"):
    if get_user_by_username(username):
        return False, "Username already exists"

    password_hash = generate_password_hash(password)
    create_user(
        {
            "username": username,
            "password_hash": password_hash,
            "full_name": full_name,
            "role": role,
            "status": "pending",
        }
    )
    return True, "User registered successfully. Access is pending Admin approval."

def logout():
    token = st.session_state.get("user", {}).get("token")
    if token:
        delete_session_token(token)

    st.session_state["user"] = None
    st.session_state["role"] = None
    
    st.session_state["_del_cookie"] = True

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
