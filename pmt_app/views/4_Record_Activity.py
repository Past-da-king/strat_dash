import streamlit as st
import auth
import database
import pandas as pd
from datetime import datetime
import os
import styles

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
            border-left: 5px solid #4caf50;
        }
        .task-card-active {
            border-left: 5px solid #0ea5e9;
        }
        .task-card-pending {
            border-left: 5px solid #ffc107;
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
        .badge-status-complete { background: rgba(16, 185, 129, 0.15) !important; color: #34d399 !important; border: 1px solid rgba(16, 185, 129, 0.3) !important; }
        .badge-status-active { background: rgba(37, 99, 235, 0.15) !important; color: #60a5fa !important; border: 1px solid rgba(37, 99, 235, 0.3) !important; }
        .badge-status-pending { background: rgba(245, 158, 11, 0.15) !important; color: #fbbf24 !important; border: 1px solid rgba(245, 158, 11, 0.3) !important; }
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
    
    # 2. Fetch Activities with responsible person filter
    # Personnel only see their own tasks. PM/Admin/Exec see all.
    task_user_filter = None if is_global_role or current_user['role'] == 'pm' else current_user['id']
    activities = database.get_baseline_schedule(project_id, user_id_filter=task_user_filter)
    
    if activities is None or activities.empty:
        st.warning("No activities found for you in this project.")
        st.stop()
    
    st.divider()
    
    # --- Completion Dialog ---
    @st.dialog("Complete Task", width="medium")
    def complete_task_dialog(activity_id, activity_name, expected_output):
        st.markdown(f"### Completing: **{activity_name}**")
        
        if expected_output:
            st.info(f"**Expected Output:** {expected_output}")
        
        st.markdown("---")
        st.markdown("**Please upload the deliverable file associated with this task:**")
        
        uploaded_file = st.file_uploader(
            "Upload Output File *",
            type=['pdf', 'docx', 'xlsx', 'png', 'jpg', 'jpeg', 'csv', 'zip'],
            key=f"upload_{activity_id}"
        )
        
        if uploaded_file is not None:
            st.success(f"📄 File selected: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")
            
            if st.button("✅ Confirm Completion", type="primary", use_container_width=True):
                # Save file to disk
                upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads', str(project_id), str(activity_id))
                os.makedirs(upload_dir, exist_ok=True)
                
                file_path = os.path.join(upload_dir, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # Save metadata to DB
                relative_path = os.path.join('uploads', str(project_id), str(activity_id), uploaded_file.name)
                database.save_task_output(activity_id, uploaded_file.name, relative_path, current_user['id'])
                
                # Update activity status
                success, msg = database.update_activity_status(activity_id, 'Complete', current_user['id'])
                if success:
                    st.success("Task completed and output uploaded!")
                    st.rerun()
                else:
                    st.error(msg)
        else:
            st.warning("You must upload the output file before marking this task as complete.")
    
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
            # 1. Header Row
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f'<div class="op-title">{row["activity_name"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="op-meta"><i class="far fa-calendar-alt"></i> Planned: {row["planned_start"].strftime("%d %b %Y")} &mdash; {row["planned_finish"]}</div>', unsafe_allow_html=True)
                
                badges_html = f'<div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:8px;">'
                resp_name = row.get('responsible_name')
                display_name = resp_name if pd.notna(resp_name) and resp_name else "Unassigned"
                badges_html += f'<span class="badge badge-user"><i class="fas fa-user-circle"></i> Assigned to: {display_name}</span>'
                
                if row.get('expected_output'):
                    badges_html += f'<span class="badge badge-output"><i class="fas fa-clipboard-list"></i> {row["expected_output"]}</span>'
                badges_html += '</div>'
                st.markdown(badges_html, unsafe_allow_html=True)
            
            with c2:
                status_class = "badge-status-complete" if status == "Complete" else ("badge-status-active" if status == "Active" else "badge-status-pending")
                st.markdown(f'<div style="text-align:right;"><span class="badge {status_class}">{status.upper()}</span></div>', unsafe_allow_html=True)
            
            # 2. Action Area (Inside the border)
            st.markdown('<div style="height:1px; background:rgba(128,128,128,0.1); margin:15px 0;"></div>', unsafe_allow_html=True)
            
            act_col1, act_col2 = st.columns([3, 1])
            with act_col1:
                if status == "Complete":
                    outputs = database.get_task_outputs(row['activity_id'])
                    if not outputs.empty:
                        st.markdown('<div style="font-size:0.75rem; color:#34d399; font-weight:700; opacity:0.8; margin-bottom:8px;">SUBMITTED DELIVERABLES:</div>', unsafe_allow_html=True)
                        for _, out in outputs.iterrows():
                            file_full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', out['file_path'])
                            if os.path.exists(file_full_path):
                                with open(file_full_path, "rb") as fp:
                                    st.markdown('<div class="download-btn">', unsafe_allow_html=True)
                                    st.download_button(
                                        out['file_name'],
                                        data=fp.read(),
                                        file_name=out['file_name'],
                                        key=f"dl_{out['output_id']}",
                                        use_container_width=False
                                    )
                                    st.markdown('</div>', unsafe_allow_html=True)
            
            with act_col2:
                if status == "Not Started":
                    st.markdown('<div class="add-btn">', unsafe_allow_html=True)
                    if st.button("Start Phase", key=f"btn_{row['activity_id']}", use_container_width=True):
                        success, msg = database.update_activity_status(row['activity_id'], 'Active', current_user['id'])
                        if success:
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                elif status == "Active":
                    st.markdown('<div class="check-btn">', unsafe_allow_html=True)
                    if st.button("Complete", key=f"btn_{row['activity_id']}", use_container_width=True, type="primary"):
                        complete_task_dialog(row['activity_id'], row['activity_name'], row.get('expected_output'))
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    is_privileged = current_user['role'] in ['admin', 'pm', 'executive']
                    if is_privileged:
                        st.markdown('<div class="refresh-btn">', unsafe_allow_html=True)
                        if st.button("Reopen Task", key=f"btn_{row['activity_id']}", use_container_width=True):
                            database.update_activity_status(row['activity_id'], 'Active', current_user['id'])
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="check-btn">', unsafe_allow_html=True)
                        st.button("Done", disabled=True, key=f"btn_{row['activity_id']}", use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)

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
