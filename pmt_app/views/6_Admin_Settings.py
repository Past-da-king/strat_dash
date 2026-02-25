import streamlit as st
import database
import auth
import styles
import pandas as pd

# Page Config
st.set_page_config(page_title="PM Tool - System Admin", layout="wide")

def admin_settings_page():
    auth.require_role(['admin', 'executive'])
    styles.global_css()
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0c4a6e 0%, #0ea5e9 100%); color: white; padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 1.5rem; box-shadow: 0 4px 12px rgba(12, 74, 110, 0.2);">
        <div style="display: flex; align-items: center; gap: 12px;">
            <i class="fas fa-shield-alt" style="font-size: 1.6rem;"></i>
            <div style="font-size: 1.6rem; font-weight: 700;">System Administration</div>
        </div>
        <div style="font-size: 0.85rem; opacity: 0.9; margin-left: 36px;">Manage user access, approvals, and system lifecycle</div>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["USERS & APPROVALS", "PROJECT ACCESS", "LOGS"])
    
    with tab1:
        st.subheader("Account Requests")
        users = database.get_all_users()
        if users.empty: st.info("No users found."); return

        # 1. Pending Approvals
        pending = users[users['status'] == 'pending']
        if not pending.empty:
            st.warning(f"{len(pending)} pending request(s).")
            for _, u in pending.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    c1.markdown(f"**{u['full_name']}** (@{u['username']}) - {u['role'].upper()}")
                    with c2:
                        st.markdown('<div class="check-btn">', unsafe_allow_html=True)
                        if st.button("Approve", key=f"app_{u['user_id']}", type="primary", use_container_width=True):
                            database.update_user_status(u['user_id'], 'approved')
                            st.success("Approved!"); st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    with c3:
                        st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
                        if st.button("Reject", key=f"rej_{u['user_id']}", use_container_width=True):
                            database.delete_user(u['user_id'])
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.success("No pending approvals.")

        st.divider()

        # 2. Active User Directory
        st.subheader("Active User Directory")
        active = users[users['status'] != 'pending']
        
        # Table Header
        h1, h2, h3, h4 = st.columns([3, 2, 2, 2])
        h1.caption("USER DETAILS")
        h2.caption("ROLE")
        h3.caption("STATUS")
        h4.caption("ACTIONS")
        
        for _, u in active.iterrows():
            with st.container():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                c1.markdown(f"**{u['full_name']}**\n@{u['username']}")
                
                # Inline Edit - Role
                current_role_idx = 0
                roles = ["pm", "executive", "team", "admin"]
                if u['role'] in roles:
                    current_role_idx = roles.index(u['role'])
                    
                new_role = c2.selectbox("Role", roles, 
                                      index=current_role_idx, 
                                      key=f"role_{u['user_id']}", label_visibility="collapsed")
                
                if new_role != u['role']:
                    if u['username'] == auth.get_current_user()['username'] and new_role != 'admin':
                         st.toast("⚠️ You cannot revoke your own admin rights!", icon="⚠️")
                    else:
                        database.update_user_role(u['user_id'], new_role)
                        st.toast(f"Updated role for {u['username']}"); st.rerun()
                
                status_color = "#4caf50" if u['status'] == 'approved' else "#ffc107"
                c3.markdown(f'<span style="background:{status_color}20; color:{status_color}; padding:3px 10px; border-radius:12px; font-size:0.8rem; font-weight:600;">{u["status"].upper()}</span>', unsafe_allow_html=True)
                
                # DANGER ZONE BUTTON INLINE
                with c4:
                    st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
                    if st.button("Delete", key=f"del_u_{u['user_id']}", use_container_width=True):
                        if u['username'] == 'admin':
                            st.error("Root Admin protected.")
                        else:
                            database.delete_user(u['user_id'])
                            st.warning(f"Deleted {u['username']}")
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                st.divider()

    with tab2:
        st.subheader("Manage Project Team Assignments")
        projects = database.get_projects(pm_id=None)
        if projects.empty: st.info("No projects created yet."); st.stop()
        
        # Use a narrower column for selection
        col_s1, col_center, col_s2 = st.columns([1, 2, 1])
        with col_center:
            # Select Project
            proj_map = {f"{r['project_number']} - {r['project_name']}": r for _, r in projects.iterrows()}
            sel_p_str = st.selectbox("Select Project to Manage", list(proj_map.keys()))
            target_p = proj_map[sel_p_str]
            p_id = target_p['project_id']
            
            st.markdown(f"**Editing Access for:** {target_p['project_name']}")
            
            # 1. Change Lead PM
            pm_users = database.get_df("SELECT user_id, full_name FROM users WHERE role IN ('pm', 'admin')")
            pm_idx = 0
            pm_ids = pm_users['user_id'].tolist()
            
            current_pm_id = target_p['pm_user_id']
            if current_pm_id in pm_ids:
                pm_idx = pm_ids.index(current_pm_id)
                
            new_pm_id = st.selectbox("Lead Project Manager", pm_users['user_id'].tolist(), 
                                   format_func=lambda x: pm_users[pm_users['user_id']==x]['full_name'].values[0],
                                   index=pm_idx)
                                   
            if new_pm_id != current_pm_id:
                st.markdown('<div class="refresh-btn">', unsafe_allow_html=True)
                if st.button("Update Lead PM", type="primary", use_container_width=True):
                    database.update_project_pm(p_id, new_pm_id, auth.get_current_user()['id'])
                    st.success("Project Manager updated successfully.")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.divider()
            
            # 2. Manage Team
            st.markdown("### Project Team Members")
            current_assigns = database.get_project_assignments(p_id)
            current_team_ids = current_assigns[current_assigns['assigned_role'] != 'pm']['user_id'].tolist()
            
            all_users = database.get_df("SELECT user_id, full_name, role FROM users WHERE status='approved'")
            avail_team = all_users[all_users['user_id'] != new_pm_id]
            
            user_map = {row['user_id']: f"{row['full_name']} ({row['role']})" for _, row in avail_team.iterrows()}
            
            valid_defaults = [uid for uid in current_team_ids if uid in user_map]
            
            new_team = st.multiselect("Assigned Staff", options=list(user_map.keys()), 
                                    format_func=lambda x: user_map[x],
                                    default=valid_defaults)
            
            st.markdown('<div class="save-btn">', unsafe_allow_html=True)
            if st.button("Update Project Team", use_container_width=True):
                database.execute_query("DELETE FROM project_assignments WHERE project_id = %s AND assigned_role != 'pm'", (p_id,), commit=True)
                for uid in new_team:
                    database.assign_user_to_project(p_id, uid, 'team', auth.get_current_user()['id'])
                st.success("Team assignments updated!")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        st.divider()

        # 3. Assign Tasks to Personnel
        st.markdown("### Specific Task Assignments")
        st.info("<i class='fas fa-info-circle fa-icon'></i> Assign specific project phases to personnel. Assigned staff will only see their own tasks on the 'Record Activity' page.")
        
        baseline_df = database.get_baseline_schedule(p_id)
        if not baseline_df.empty:
            # Create user selection list for the editor
            resp_user_map = {row['full_name']: row['user_id'] for _, row in all_users.iterrows()}
            user_list = ["Unassigned"] + list(resp_user_map.keys())
            
            # Prepare data for editor
            editor_df = baseline_df[['activity_id', 'activity_name', 'responsible_name']].copy()
            editor_df['responsible_name'] = editor_df['responsible_name'].fillna("Unassigned")
            
            edited_tasks = st.data_editor(
                editor_df,
                key=f"task_editor_{p_id}",
                use_container_width=True,
                disabled=["activity_id", "activity_name"],
                column_config={
                    "activity_id": None, # Hide ID
                    "activity_name": "Task/Phase",
                    "responsible_name": st.column_config.SelectboxColumn("Responsible Person", options=user_list)
                }
            )
            
            st.markdown('<div class="save-btn">', unsafe_allow_html=True)
            if st.button("Save Task Assignments", use_container_width=True):
                for _, row in edited_tasks.iterrows():
                    new_resp_name = row['responsible_name']
                    new_resp_id = resp_user_map.get(new_resp_name) if new_resp_name != "Unassigned" else None
                    
                    database.execute_query(
                        "UPDATE baseline_schedule SET responsible_user_id = %s WHERE activity_id = %s",
                        (new_resp_id, row['activity_id']),
                        commit=True
                    )
                st.success("Task assignments saved!")
                st.rerun()
        else:
            st.warning("No activities defined for this project.")

    with tab3:
        st.subheader("System Access Logs")
        logs = database.get_df("SELECT * FROM audit_log ORDER BY changed_at DESC LIMIT 50")
        if not logs.empty:
            st.dataframe(logs, use_container_width=True, hide_index=True)
        else:
            st.info("No system logs recorded yet.")

if __name__ == "__main__":
    admin_settings_page()
