import streamlit as st
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_user_by_username, create_user

def init_session():
    if 'user' not in st.session_state:
        st.session_state['user'] = None
    if 'role' not in st.session_state:
        st.session_state['role'] = None

def login(username, password):
    user = get_user_by_username(username)
    if user and check_password_hash(user['password_hash'], password):
        # We allow login even if pending/inactive, but handle visibility in main.py
        st.session_state['user'] = {
            'id': user['user_id'],
            'username': user['username'],
            'full_name': user['full_name'],
            'role': user['role'],
            'status': user['status']
        }
        st.session_state['role'] = user['role']
        return True
    return False

def register(username, password, full_name, role='pm'):
    if get_user_by_username(username):
        return False, "Username already exists"
    
    password_hash = generate_password_hash(password)
    create_user({
        'username': username,
        'password_hash': password_hash,
        'full_name': full_name,
        'role': role,
        'status': 'pending'
    })
    return True, "User registered successfully. Access is pending Admin approval."

def logout():
    st.session_state['user'] = None
    st.session_state['role'] = None
    st.rerun()

def is_logged_in():
    return st.session_state.get('user') is not None

def require_role(roles):
    if not is_logged_in():
        st.error("Please login to access this page")
        st.stop()
    
    user = get_current_user()
    if user.get('status') != 'approved':
        st.error("Access Denied: Your account is pending administrator approval.")
        st.stop()
        
    user_role = st.session_state.get('role')
    if user_role not in roles and user_role != 'admin':
        st.error("You do not have permission to view this page")
        st.stop()

def get_current_user():
    return st.session_state.get('user')
