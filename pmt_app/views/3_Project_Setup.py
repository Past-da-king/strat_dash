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
    <div style="background: linear-gradient(135deg, #2c5aa0 0%, #5fa2e8 100%); color: white; padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 2rem; box-shadow: 0 4px 12px rgba(44, 90, 160, 0.2);">
        <div style="display: flex; align-items: center; gap: 15px;">
            <i class="fas fa-building" style="font-size: 2.2rem;"></i>
            <div style="font-size: 2.2rem; font-weight: 700; letter-spacing: -1px;">Setup New Project</div>
        </div>
        <div style="font-size: 1rem; opacity: 0.9; margin-left: 50px;">Initialize a new project, assign teams, and set baseline schedules.</div>
    </div>
    """, unsafe_allow_html=True)
    
    tab_manual, tab_import = st.tabs(["MANUAL ENTRY", "EXCEL IMPORT"])
    
    with tab_manual:
        st.markdown("### Project Basics")
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
                current_user = auth.get_current_user()
                if current_user['role'] == 'admin':
                    pm_options = database.get_df("SELECT user_id, full_name FROM users WHERE role = 'pm'")
                    pm_map = {row['full_name']: row['user_id'] for _, row in pm_options.iterrows()}
                    selected_pm_name = st.selectbox("Assign Project Manager", list(pm_map.keys()))
                    pm_id = pm_map[selected_pm_name]
                else:
                    pm_id = current_user['id']
                    st.info(f"Project will be assigned to you: **{current_user['full_name']}**")
                
                # Team Assignment
                team_options = database.get_df("SELECT user_id, full_name, role FROM users WHERE status = 'approved'")
                team_options = team_options[team_options['user_id'] != pm_id]
                
                team_map = {f"{row['full_name']} ({row['role']})": row['user_id'] for _, row in team_options.iterrows()}
                assigned_team = st.multiselect("Assign Project Team", list(team_map.keys()))
            
            st.markdown('<div class="add-btn">', unsafe_allow_html=True)
            submit = st.form_submit_button("Create Project & Plan", type="primary", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown("---")
            st.subheader("Project Plan (Baseline Schedule)")
            st.info("<i class='fas fa-info-circle fa-icon'></i> Assign budget, dates, responsible person, and expected outputs to project phases.")
            
            # Build user map for responsible person selection
            all_users = database.get_df("SELECT user_id, full_name FROM users WHERE status = 'approved'")
            user_name_list = ["Unassigned"] + all_users['full_name'].tolist()
            
            # Data editor with new columns
            if 'activity_data' not in st.session_state:
                st.session_state.activity_data = [
                    {'activity_name': 'Initial Phase', 'planned_start': start_date, 'planned_finish': start_date, 'budgeted_cost': 0.0, 'responsible_person': 'Unassigned', 'expected_output': ''},
                    {'activity_name': 'Execution Phase', 'planned_start': start_date, 'planned_finish': end_date, 'budgeted_cost': 0.0, 'responsible_person': 'Unassigned', 'expected_output': ''}
                ]
            
            plan_df = st.data_editor(
                st.session_state.activity_data,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "activity_name": "Activity/Phase Name",
                    "planned_start": st.column_config.DateColumn("Start Date"),
                    "planned_finish": st.column_config.DateColumn("Finish Date"),
                    "budgeted_cost": st.column_config.NumberColumn("Budget (R)", min_value=0.0),
                    "responsible_person": st.column_config.SelectboxColumn("Responsible Person", options=user_name_list),
                    "expected_output": st.column_config.TextColumn("Expected Output", help="e.g. Survey Report PDF, Completion Certificate")
                }
            )

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
                        creator_id = auth.get_current_user()['id']
                        project_id = database.create_project(data, creator_id)
                        
                        # 1. Assign Lead PM
                        database.assign_user_to_project(project_id, pm_id, 'pm', creator_id)
                        
                        # 2. Assign Team Members
                        if assigned_team:
                            for member_key in assigned_team:
                                member_id = team_map[member_key]
                                database.assign_user_to_project(project_id, member_id, 'team', creator_id)
                        
                        # 3. Add Baseline Activities (with responsible person + expected output)
                        for _, row in pd.DataFrame(plan_df).iterrows():
                            responsible_user_id = None
                            resp_name = row.get('responsible_person', 'Unassigned')
                            if resp_name and resp_name != 'Unassigned':
                                match = all_users[all_users['full_name'] == resp_name]
                                if not match.empty:
                                    responsible_user_id = int(match.iloc[0]['user_id'])
                            
                            database.add_baseline_activity({
                                'project_id': project_id,
                                'activity_name': row['activity_name'],
                                'planned_start': row['planned_start'].strftime('%Y-%m-%d') if hasattr(row['planned_start'], 'strftime') else row['planned_start'],
                                'planned_finish': row['planned_finish'].strftime('%Y-%m-%d') if hasattr(row['planned_finish'], 'strftime') else row['planned_finish'],
                                'budgeted_cost': row['budgeted_cost'],
                                'responsible_user_id': responsible_user_id,
                                'expected_output': row.get('expected_output', '')
                            })
                        
                        st.success(f"Project and Plan Created Successfully! ID: {project_id}")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error creating project: {e}")

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
