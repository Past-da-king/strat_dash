import streamlit as st
import pandas as pd
from datetime import datetime
import auth
import database
import os
import styles

# Page Config
st.set_page_config(page_title="PM Tool - Project Setup", layout="wide")

def project_setup_page():
    auth.require_role(['pm', 'admin', 'executive'])
    styles.global_css()
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0c4a6e 0%, #0ea5e9 100%); color: white; padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 2rem; box-shadow: 0 4px 12px rgba(12, 74, 110, 0.2);">
        <div style="display: flex; align-items: center; gap: 15px;">
            <i class="fas fa-sliders-h" style="font-size: 2.2rem;"></i>
            <div style="font-size: 2.2rem; font-weight: 700; letter-spacing: -1px;">Project Administration</div>
        </div>
        <div style="font-size: 1rem; opacity: 0.9; margin-left: 50px;">Configure project structures, manage dependencies, and control team access.</div>
    </div>
    """, unsafe_allow_html=True)
    
    tab_manual, tab_import, tab_manage = st.tabs(["CREATE PROJECT", "EXCEL IMPORT", "MANAGE PLAN"])
    
    current_user = auth.get_current_user()
    is_admin_exec = current_user['role'] in ['admin', 'executive']

    with tab_manual:
        st.markdown("### New Project Configuration")
        with st.form("manual_project_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Project Name *")
                number = st.text_input("Project Number *")
                client = st.text_input("Client Name")
                budget = st.number_input("Total Contract Value (R) *", min_value=0.0)
            
            with col2:
                start_date = st.date_input("Planned Start Date")
                end_date = st.date_input("Target Completion Date")
                
                # PM Assignment (RBAC)
                if is_admin_exec:
                    pm_options = database.get_df("SELECT user_id, full_name FROM users WHERE role = 'pm'")
                    pm_map = {row['full_name']: row['user_id'] for _, row in pm_options.iterrows()}
                    selected_pm_name = st.selectbox("Assign Project Manager", list(pm_map.keys()))
                    pm_id = pm_map[selected_pm_name]
                else:
                    pm_id = current_user['id']
                    st.info(f"Project will be assigned to you: **{current_user['full_name']}**")
            
            st.markdown('<div class="add-btn">', unsafe_allow_html=True)
            submit = st.form_submit_button("Create Initial Project", type="primary", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            if submit:
                if not name or not number or budget <= 0:
                    st.error("Please fill in name, number and contract value.")
                else:
                    data = {
                        'project_name': name,
                        'project_number': number,
                        'client': client,
                        'total_budget': budget,
                        'start_date': start_date.strftime('%Y-%m-%d'),
                        'target_end_date': end_date.strftime('%Y-%m-%d'),
                        'pm_user_id': pm_id
                    }
                    try:
                        creator_id = current_user['id']
                        project_id = database.create_project(data, creator_id)
                        database.assign_user_to_project(project_id, pm_id, 'pm', creator_id)
                        st.success(f"Project '{name}' created successfully! ID: {project_id}")
                        st.info("💡 Next: Use the 'MANAGE PLAN' tab to add tasks and dependencies.")
                    except Exception as e:
                        st.error(f"Error: {e}")

    with tab_manage:
        st.markdown("### Edit Existing Baseline Plan")
        projects = database.get_projects(user_id=None if is_admin_exec else current_user['id'])
        
        if projects.empty:
            st.info("No projects available to manage.")
        else:
            p_map = {f"{r['project_number']} - {r['project_name']}": r['project_id'] for _, r in projects.iterrows()}
            selected_p = st.selectbox("Select Project to Manage", list(p_map.keys()), key="manage_p_sel")
            p_id = p_map[selected_p]
            
            # Fetch current schedule
            current_plan = database.get_baseline_schedule(p_id)
            all_users = database.get_df("SELECT user_id, full_name FROM users WHERE status = 'approved'")
            user_id_to_name = {row['user_id']: row['full_name'] for _, row in all_users.iterrows()}
            user_name_to_id = {v: k for k, v in user_id_to_name.items()}
            
            # Helper for dependency mapping
            act_id_to_name = {row['activity_id']: row['activity_name'] for _, row in current_plan.iterrows()} if not current_plan.empty else {}
            act_name_to_id = {v: k for k, v in act_id_to_name.items()}
            
            if current_plan.empty:
                st.info("This project has no activities. Start by adding a row below.")
                # Seed an empty row for the editor
                current_plan = pd.DataFrame(columns=['activity_id', 'activity_name', 'planned_start', 'planned_finish', 'budgeted_cost', 'responsible_name', 'depends_on_name', 'expected_output', 'status'])
            else:
                current_plan['responsible_name'] = current_plan['responsible_user_id'].map(user_id_to_name).fillna("Unassigned")
                current_plan['depends_on_name'] = current_plan['depends_on'].map(act_id_to_name).fillna("None")
                
                # Convert strings to datetime objects for st.data_editor compatibility
                current_plan['planned_start'] = pd.to_datetime(current_plan['planned_start']).dt.date
                current_plan['planned_finish'] = pd.to_datetime(current_plan['planned_finish']).dt.date

            edited_df = st.data_editor(
                current_plan[['activity_id', 'activity_name', 'planned_start', 'planned_finish', 'budgeted_cost', 'responsible_name', 'depends_on_name', 'expected_output', 'status']],
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "activity_id": st.column_config.NumberColumn("ID", disabled=True),
                    "activity_name": "Activity Name",
                    "planned_start": st.column_config.DateColumn("Start"),
                    "planned_finish": st.column_config.DateColumn("Finish"),
                    "budgeted_cost": st.column_config.NumberColumn("Budget (R)"),
                    "responsible_name": st.column_config.SelectboxColumn("Responsible", options=list(user_name_to_id.keys())),
                    "depends_on_name": st.column_config.SelectboxColumn("Predecessor", options=["None"] + list(act_id_to_name.values())),
                    "status": st.column_config.SelectboxColumn("Status", options=["Not Started", "Active", "Complete"])
                },
                key="plan_editor"
            )

            st.markdown('<div class="save-btn">', unsafe_allow_html=True)
            if st.button("Save Changes to Plan", use_container_width=True, type="primary"):
                try:
                    # Detect Deletions
                    if not current_plan.empty:
                        original_ids = set(current_plan['activity_id'].tolist())
                        final_ids = set(edited_df['activity_id'].dropna().tolist())
                        deleted_ids = original_ids - final_ids
                        for d_id in deleted_ids:
                            database.delete_baseline_activity(d_id)

                    # Update/Insert
                    for _, row in edited_df.iterrows():
                        data = {
                            "activity_name": row['activity_name'],
                            "planned_start": str(row['planned_start']),
                            "planned_finish": str(row['planned_finish']),
                            "budgeted_cost": row['budgeted_cost'],
                            "responsible_user_id": user_name_to_id.get(row['responsible_name']),
                            "depends_on": act_name_to_id.get(row['depends_on_name']),
                            "expected_output": row['expected_output'],
                            "status": row['status'],
                            "project_id": p_id
                        }
                        
                        if pd.notna(row.get('activity_id')):
                            database.update_baseline_activity(row['activity_id'], data)
                        else:
                            database.add_baseline_activity(data)
                    
                    st.success("Plan updated successfully!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving plan: {e}")
            st.markdown('</div>', unsafe_allow_html=True)

    with tab_import:
        # Download Section
        # Get path relative to this script: pages/ -> pmt_app/ -> project_root/ -> templates/
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        template_path = os.path.join(root_dir, 'templates', 'Project_Template.xlsx')
        if os.path.exists(template_path):
            with open(template_path, "rb") as f:
                st.markdown('<div class="download-btn">', unsafe_allow_html=True)
                st.download_button(
                    label="Download Blank Project Template",
                    data=f,
                    file_name="Project_Template.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="Download the official blank Excel template to fill in project data.",
                    use_container_width=True
                )
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("⚠️ Template file not found in /templates folder.")

        st.info("Fill out the downloaded template before uploading below. The template now includes **Responsible (Username)** and **Expected Output** columns.")
        
        uploaded_file = st.file_uploader("Upload Project Excel", type=["xlsx"])
        
        if uploaded_file:
            import importer
            st.markdown('<div class="refresh-btn">', unsafe_allow_html=True)
            if st.button("Start Import", use_container_width=True):
                try:
                    with st.spinner("Processing Excel..."):
                        project_id = importer.import_project(uploaded_file, auth.get_current_user()['id'])
                        st.success(f"Project Imported Successfully! ID: {project_id}")
                except Exception as e:
                    st.error(f"Import Failed: {e}")
            st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    project_setup_page()
