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
    
    t1, t2, t3 = st.tabs(["USER MANAGEMENT", "AUDIT LOGS", "DATA MANAGEMENT"])
    
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

    with t3:
        import data_mgmt
        st.subheader("Database Backup & Recovery")
        st.info("Export your data to a multi-sheet Excel file or restore it from a previous backup.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📤 Export Data")
            st.write("Download the entire database (all tables).")
            
            # --- Option A: SQLite DB File ---
            st.markdown("**Option A: Full SQLite Database (.db)**")
            db_file = data_mgmt.get_sqlite_db_file()
            if db_file:
                st.markdown('<div class="download-btn">', unsafe_allow_html=True)
                st.download_button(
                    "DOWNLOAD .DB FILE",
                    data=db_file,
                    file_name="pm_tool_backup.db",
                    mime="application/x-sqlite3",
                    use_container_width=True
                )
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("SQLite backup only available in local mode.")

            st.markdown('<div style="height:15px"></div>', unsafe_allow_html=True)

            # --- Option C: Full System Archive ---
            st.markdown("**Option C: Full System Archive (.ZIP)**")
            st.write("Best for full backups. Includes DB + Excel + All Documents.")
            st.markdown('<div class="download-btn">', unsafe_allow_html=True)
            if st.button("GENERATE FULL ARCHIVE", use_container_width=True):
                with st.spinner("Packaging all documents and data..."):
                    zip_data = data_mgmt.generate_full_archive()
                    st.download_button(
                        "DOWNLOAD FULL ARCHIVE (.ZIP)",
                        data=zip_data,
                        file_name=f"StratEdge_Full_Backup_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col2:
            st.markdown("#### 📥 Import Data")
            st.warning("⚠️ **DANGER**: Importing data will DELETE all current information and replace it with the contents of the Excel file.")
            uploaded_file = st.file_uploader("Upload Backup Excel", type=["xlsx"])
            if uploaded_file:
                st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
                if st.button("RESTORE DATABASE", use_container_width=True):
                    success, msg = data_mgmt.import_all_data(uploaded_file)
                    if success:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.error(msg)
                st.markdown('</div>', unsafe_allow_html=True)

        st.divider()
        st.markdown("#### 🛡️ Advanced Actions")
        if st.checkbox("Enable Destructive Actions"):
            st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
            if st.button("DELETE ALL DATA (FACTORY RESET)", use_container_width=True):
                tables = ["task_outputs", "risks", "audit_log", "project_assignments", "expenditure_log", "activity_log", "baseline_schedule", "projects", "users"]
                for t in tables:
                    database.execute_query(f"DELETE FROM {t}", commit=True)
                st.success("All data cleared. Please register a new admin user.")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    admin_panel()
