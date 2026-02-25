import streamlit as st
import auth
import database
import pandas as pd
import styles
from werkzeug.security import generate_password_hash

# Page Config
st.set_page_config(page_title="PM Tool - Admin Panel", layout="wide")

def admin_panel():
    auth.require_role(['admin', 'executive'])
    styles.global_css()
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0c4a6e 0%, #0ea5e9 100%); color: white; padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 1.5rem; box-shadow: 0 4px 12px rgba(12, 74, 110, 0.2);">
        <div style="display: flex; align-items: center; gap: 12px;">
            <i class="fas fa-tools" style="font-size: 1.6rem;"></i>
            <div style="font-size: 1.6rem; font-weight: 700;">Admin Panel</div>
        </div>
        <div style="font-size: 0.85rem; opacity: 0.9; margin-left: 36px;">User Management & Audit Trails</div>
    </div>
    """, unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["USER MANAGEMENT", "AUDIT LOGS"])
    
    with t1:
        st.subheader("Current Users")
        users = database.get_df("SELECT user_id, username, role, full_name, status FROM users")
        st.dataframe(users, use_container_width=True, hide_index=True)
        
        st.divider()
        col_s1, col_center, col_s2 = st.columns([1, 2, 1])
        with col_center:
            with st.form("add_user_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_user = st.text_input("Username")
                    new_pass = st.text_input("Password", type="password")
                with col2:
                    new_role = st.selectbox("Role", ["executive", "pm", "team", "admin"])
                    new_name = st.text_input("Full Name")
                
                st.markdown('<div class="add-btn">', unsafe_allow_html=True)
                submit_user = st.form_submit_button("Add User", use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                if submit_user:
                    if not new_user or not new_pass or not new_name:
                        st.error("Please fill in all fields.")
                    else:
                        try:
                            database.execute_query(
                                "INSERT INTO users (username, password_hash, role, full_name, status) VALUES (%s, %s, %s, %s, %s)",
                                (new_user, generate_password_hash(new_pass), new_role, new_name, 'approved'),
                                commit=True
                            )
                            st.success(f"User {new_user} created successfully.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

    with t2:
        st.subheader("System Audit Log")
        logs = database.get_df('''
            SELECT al.*, u.username 
            FROM audit_log al 
            LEFT JOIN users u ON al.changed_by = u.user_id 
            ORDER BY changed_at DESC
        ''')
        st.dataframe(logs, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    admin_panel()
