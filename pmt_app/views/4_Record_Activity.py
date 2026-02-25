import streamlit as st
import auth
import database
import pandas as pd
from datetime import datetime
import os
import styles
import base64

# Page Config
st.set_page_config(page_title="PM Tool - Record Activity", layout="wide")

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pmt_app', 'uploads')
# Fix path for when running from pmt_app directory
if not os.path.exists(UPLOADS_DIR):
    UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')

def record_activity_page():
    auth.require_role(['team', 'pm', 'admin', 'executive'])
    styles.global_css()
    
    st.markdown("""
    <style>
        .task-card {
            background: rgba(128, 128, 128, 0.05);
            border-radius: 12px;
            padding: 1.2rem;
            margin-bottom: 0.8rem;
            border: 1px solid rgba(128, 128, 128, 0.1);
            box-shadow: 0 2px 8px rgba(0,0,0,0.03);
            transition: all 0.3s ease;
        }
        .task-card:hover {
            box-shadow: 0 6px 16px rgba(0,0,0,0.08);
            transform: translateY(-2px);
        }
        .task-card-complete {
            border-left: 5px solid #10b981;
        }
        .task-card-active {
            border-left: 5px solid #f59e0b;
        }
        .task-card-pending {
            border-left: 5px solid #ef4444;
        }
        .badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-right: 6px;
        }
        .badge-user { 
            background: rgba(59, 130, 246, 0.15) !important; color: #60a5fa !important; 
            border: 1px solid rgba(59, 130, 246, 0.3) !important;
        }
        .badge-output { 
            background: rgba(245, 158, 11, 0.1) !important; color: #fbbf24 !important;
            border: 1px solid rgba(245, 158, 11, 0.2) !important;
        }
        .badge-status-complete { background: rgba(16, 185, 129, 0.15) !important; color: #10b981 !important; border: 1px solid rgba(16, 185, 129, 0.3) !important; }
        .badge-status-active { background: rgba(245, 158, 11, 0.15) !important; color: #f59e0b !important; border: 1px solid rgba(245, 158, 11, 0.3) !important; }
        .badge-status-pending { background: rgba(239, 68, 68, 0.15) !important; color: #ef4444 !important; border: 1px solid rgba(239, 68, 68, 0.3) !important; }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 0.5rem;">
            <i class="fas fa-bolt" style="font-size: 2rem; color: #fbbf24;"></i>
            <h1 style="margin: 0;">Activity Status Management</h1>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("Update the current progress of project phases. *Strict dependency rules apply.*")
    
    # 1. Fetch Projects (RBAC)
    current_user = auth.get_current_user()
    is_global_role = current_user['role'] in ['admin', 'executive']
    
    # If not global role, filter projects where they are assigned (either as PM or team)
    user_id_filter = None if is_global_role else current_user['id']
    projects = database.get_projects(user_id=user_id_filter)
    
    if projects.empty:
        st.info("No projects assigned to you found.")
        st.stop()
        
    project_map = {f"{row['project_number']} - {row['project_name']}": row['project_id'] 
                   for _, row in projects.iterrows()}
    project_list = list(project_map.keys())
    
    selected_project_str = st.selectbox("Select Project", project_list)
    project_id = project_map[selected_project_str]
    
    # --- ACTIVITY VIEW FILTER ---
    st.markdown('<div style="margin-bottom: 1rem;">', unsafe_allow_html=True)
    view_mode = st.radio("Display Scope", ["All Activities", "My Activities"], horizontal=True, label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. Fetch Activities
    # Fetch all for the project first
    all_activities = database.get_baseline_schedule(project_id)
    
    if all_activities is None or all_activities.empty:
        st.warning("No activities found for this project.")
        st.stop()

    # Apply filter based on toggle
    if view_mode == "My Activities":
        activities = all_activities[all_activities['responsible_user_id'] == current_user['id']]
        if activities.empty:
            st.info("You have no activities assigned to you in this project.")
            st.stop()
    else:
        activities = all_activities
    
    st.divider()
    
    # --- Submission Dialog ---
    @st.dialog("Submit Documents", width="medium")
    def submit_document_dialog(activity_id, activity_name, doc_type):
        st.markdown(f"### Submitting {doc_type}: **{activity_name}**")
        st.info(f"Uploading **{doc_type}(s)** is required to progress this task.")
        st.markdown("---")
        
        uploaded_files = st.file_uploader(
            f"Select {doc_type}(s) *",
            type=['pdf', 'docx', 'xlsx', 'png', 'jpg', 'jpeg', 'csv', 'zip'],
            accept_multiple_files=True,
            key=f"upload_{activity_id}_{doc_type}"
        )
        
        if uploaded_files:
            st.success(f"📂 {len(uploaded_files)} file(s) selected.")
            if st.button(f"✅ Upload {len(uploaded_files)} Document(s)", type="primary", use_container_width=True):
                for uploaded_file in uploaded_files:
                    # Determine blob name (path inside the container)
                    blob_name = f"uploads/{project_id}/{activity_id}/{uploaded_file.name}"
                    
                    # Upload to Azure
                    database.upload_file_to_azure(uploaded_file.getvalue(), blob_name)
                    
                    # Save record to DB (using the blob_name as the file_path)
                    database.save_task_output(activity_id, uploaded_file.name, blob_name, current_user['id'], doc_type=doc_type)
                
                # Automatic status progression
                if doc_type == "First Draft":
                    database.update_activity_status(activity_id, 'Active', current_user['id'])
                    st.success("First Draft(s) uploaded! Task is now officially STARTED.")
                elif doc_type == "Final Document":
                    database.update_activity_status(activity_id, 'Complete', current_user['id'])
                    st.success("Final Document(s) uploaded! Task is now COMPLETE.")
                else:
                    st.success(f"{len(uploaded_files)} {doc_type}(s) uploaded successfully.")
                
                st.rerun()
    
    # --- Summary Stats (Scoped to visible activities) ---
    total = len(activities)
    completed = len(activities[activities['status'] == 'Complete'])
    active = len(activities[activities['status'] == 'Active'])
    pending = total - completed - active
    
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.markdown(f'<div class="stat-card"><div class="stat-label">Total Tasks</div><div class="stat-value-container"><div class="stat-value">{total}</div></div></div>', unsafe_allow_html=True)
    with s2:
        pct_val = f"{completed/total*100:.0f}%" if total > 0 else "0%"
        st.markdown(f'<div class="stat-card"><div class="stat-label">Completed</div><div class="stat-value-container"><div class="stat-value">{completed}</div><div class="stat-delta">↑ {pct_val}</div></div></div>', unsafe_allow_html=True)
    with s3:
        st.markdown(f'<div class="stat-card"><div class="stat-label">In Progress</div><div class="stat-value-container"><div class="stat-value">{active}</div></div></div>', unsafe_allow_html=True)
    with s4:
        st.markdown(f'<div class="stat-card"><div class="stat-label">Not Started</div><div class="stat-value-container"><div class="stat-value">{pending}</div></div></div>', unsafe_allow_html=True)
    
    st.divider()
    st.subheader("Current Operational Status")
    
    # Sort by planned start
    activities['planned_start'] = pd.to_datetime(activities['planned_start'])
    activities = activities.sort_values('planned_start')
    
    for _, row in activities.iterrows():
        status = row['status'] or 'Not Started'
        
        with st.container(border=True):
            # --- EVEN MORE COMPACT HORIZONTAL LAYOUT ---
            main_col1, main_col2, main_col3 = st.columns([2.5, 1.5, 2.0])
            
            with main_col1:
                st.markdown(f"""
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
                        <div class="op-title" style="margin-bottom:0;">{row["activity_name"]}</div>
                    </div>
                    <div style="display:flex; gap:8px; align-items:center;">
                        <span class="badge {'badge-status-complete' if status == 'Complete' else ('badge-status-active' if status == 'Active' else 'badge-status-pending')}" style="margin:0;">
                            {status.upper()}
                        </span>
                        <div class="op-meta" style="margin:0;"><i class="far fa-calendar-alt"></i> {row["planned_start"].strftime("%d %b")} - {row["planned_finish"]}</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with main_col2:
                resp_name = row.get('responsible_name')
                display_name = resp_name if pd.notna(resp_name) and resp_name else "Unassigned"
                st.markdown(f"""
                    <div style="font-size:0.7rem; font-weight:600; color:#94a3b8; margin-bottom:2px; text-transform:uppercase;">Assignment</div>
                    <div style="font-size:0.8rem; color:#e2e8f0; margin-bottom:6px;"><i class="fas fa-user-circle" style="color:#38bdf8;"></i> {display_name}</div>
                    
                    <div style="font-size:0.7rem; font-weight:600; color:#94a3b8; margin-bottom:2px; text-transform:uppercase;">Deliverable</div>
                    <div style="font-size:0.8rem; color:#fbbf24; font-style:italic;"><i class="fas fa-file-contract"></i> {row.get('expected_output') or 'None'}</div>
                """, unsafe_allow_html=True)

            with main_col3:
                # --- Actions Column (Side-by-Side) ---
                if status == "Not Started":
                    st.markdown('<div class="upload-btn">', unsafe_allow_html=True)
                    if st.button("Start Phase", key=f"btn_{row['activity_id']}", use_container_width=True):
                        submit_document_dialog(row['activity_id'], row['activity_name'], "First Draft")
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown('<div style="text-align:center; font-size:0.65rem; color:#ef4444; font-weight:700; margin-top:4px;">REQUIRES FIRST DRAFT</div>', unsafe_allow_html=True)
                
                elif status == "Active":
                    has_risks = database.has_open_risks(row['activity_id'])
                    
                    if has_risks:
                        st.markdown('<div style="background:rgba(239,68,68,0.1); border:1px solid #ef4444; border-radius:6px; padding:4px; text-align:center; margin-bottom:8px;">', unsafe_allow_html=True)
                        st.markdown('<div style="color:#ef4444; font-size:0.7rem; font-weight:700;"><i class="fas fa-exclamation-triangle"></i> OPEN RISKS LINKED</div>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    # SIDE-BY-SIDE BUTTONS
                    btn_c1, btn_c2 = st.columns(2)
                    with btn_c1:
                        st.markdown('<div class="add-btn">', unsafe_allow_html=True)
                        if st.button("Upload Draft", key=f"draft_{row['activity_id']}", use_container_width=True):
                            submit_document_dialog(row['activity_id'], row['activity_name'], "Regular Draft")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with btn_c2:
                        st.markdown('<div class="check-btn">', unsafe_allow_html=True)
                        # REMOVED HARD GATE: button is no longer disabled by has_risks
                        if st.button("Complete", key=f"btn_{row['activity_id']}", use_container_width=True, type="primary"):
                            submit_document_dialog(row['activity_id'], row['activity_name'], "Final Document")
                        st.markdown('</div>', unsafe_allow_html=True)
                
                elif status == "Complete":
                    is_privileged = current_user['role'] in ['admin', 'pm', 'executive']
                    if is_privileged:
                        st.markdown('<div class="refresh-btn">', unsafe_allow_html=True)
                        if st.button("Reopen Task", key=f"btn_{row['activity_id']}", use_container_width=True):
                            database.update_activity_status(row['activity_id'], 'Active', current_user['id'])
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="check-btn" style="opacity:0.5;">', unsafe_allow_html=True)
                        st.button("Done", disabled=True, key=f"btn_{row['activity_id']}", use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)

            # Sub-row for existing deliverables (if any)
            if status != "Not Started":
                outputs = database.get_task_outputs(row['activity_id'])
                if not outputs.empty:
                    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
                    with st.expander(f"VIEW SUBMITTED DOCUMENTS ({len(outputs)})", expanded=False, icon=":material/folder_open:"):
                        # List links vertically for a cleaner "File Explorer" feel
                        for _, out in outputs.iterrows():
                            blob_name = out['file_path']
                            data = None
                            try:
                                data = database.download_file_from_azure(blob_name)
                            except:
                                pass

                            if data:
                                b64 = base64.b64encode(data).decode()
                                
                                # Determine icon based on doc_type or filename
                                icon = "fa-file-pdf" if out['file_name'].endswith('.pdf') else "fa-file-alt"
                                label_color = "#34d399" if out.get('doc_type') == 'Final Document' else "#38bdf8"
                                
                                st.markdown(f"""
                                    <div style="margin-bottom: 8px; display: flex; align-items: center; gap: 10px;">
                                        <i class="fas {icon}" style="color: {label_color};"></i>
                                        <a href="data:application/octet-stream;base64,{b64}" download="{out['file_name']}" 
                                           style="color: {label_color}; text-decoration: none; font-size: 0.85rem; font-weight: 500;">
                                           {out['file_name']}
                                        </a>
                                        <span style="font-size: 0.7rem; color: #94a3b8; margin-left: auto;">
                                            Uploaded by {out['uploader_name']} on {str(out['uploaded_at'])[:10]}
                                        </span>
                                    </div>
                                """, unsafe_allow_html=True)
        
        st.markdown('<div style="height:5px;"></div>', unsafe_allow_html=True)

    # Activity Audit Log
    with st.expander("Activity Audit Log (History)"):
        logs = database.get_df('''
            SELECT al.event_type, al.event_date, bs.activity_name, u.full_name as recorded_by
            FROM activity_log al
            JOIN baseline_schedule bs ON al.activity_id = bs.activity_id
            JOIN users u ON al.recorded_by = u.user_id
            WHERE bs.project_id = %s
            ORDER BY al.log_id DESC
        ''', (project_id,))
        if not logs.empty:
            st.dataframe(logs, use_container_width=True, hide_index=True)
        else:
            st.caption("No activity events recorded yet.")

if __name__ == "__main__":
    record_activity_page()
