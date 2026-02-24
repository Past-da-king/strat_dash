import streamlit as st
import auth
import database
import pandas as pd
from datetime import datetime
import styles

# Page Config
st.set_page_config(page_title="PM Tool - Record Expenditure", layout="wide")

def record_exp_page():
    auth.require_role(['team', 'pm', 'admin', 'executive'])
    styles.global_css()
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #2c5aa0 0%, #5fa2e8 100%); color: white; padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 1.5rem; box-shadow: 0 4px 12px rgba(44, 90, 160, 0.2);">
        <div style="display: flex; align-items: center; gap: 12px;">
            <i class="fas fa-money-bill-wave" style="font-size: 1.6rem;"></i>
            <div style="font-size: 1.6rem; font-weight: 700;">Record Expenditure</div>
        </div>
        <div style="font-size: 0.85rem; opacity: 0.9; margin-left: 36px;">Log project costs against activities</div>
    </div>
    """, unsafe_allow_html=True)
    
    # 1. Fetch Projects (RBAC)
    current_user = auth.get_current_user()
    is_global_role = current_user['role'] in ['admin', 'executive', 'team']
    
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
    
    # 2. Setup Activity Mapping (Filtered by responsible person for non-global roles)
    task_user_filter = None if is_global_role or current_user['role'] == 'pm' else current_user['id']
    activities = database.get_baseline_schedule(project_id, user_id_filter=task_user_filter)
    
    act_map = {"None / Overhead": None}
    if activities is not None and not activities.empty:
        for _, row in activities.iterrows():
            act_map[f"{row['activity_name']}"] = row['activity_id']
    
    act_list = list(act_map.keys())
    selected_act_str = st.selectbox("Linked Activity (Optional)", act_list)
    activity_id = act_map[selected_act_str]

    # 3. Entry Form - Constrain width
    col_space1, col_center, col_space2 = st.columns([1, 2, 1])
    
    with col_center:
        with st.form("exp_log_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                category = st.selectbox("Category", ["Labour", "Material", "Vehicle", "Diesel", "Other"])
                amount = st.number_input("Amount (R)", min_value=0.01, step=100.0)
                spend_date = st.date_input("Spend Date", datetime.now())
            
            with col2:
                reference = st.text_input("Reference (Invoice / PO) *")
                description = st.text_area("Description")
            
            st.markdown('<div class="save-btn">', unsafe_allow_html=True)
            submit = st.form_submit_button("Log Expenditure", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        if submit:
            if not reference:
                st.error("Reference ID is required for verification.")
            else:
                try:
                    data = {
                        'project_id': project_id,
                        'activity_id': activity_id,
                        'category': category,
                        'description': description,
                        'reference_id': reference,
                        'amount': amount,
                        'spend_date': spend_date.strftime('%Y-%m-%d')
                    }
                    database.add_expenditure(data, auth.get_current_user()['id'])
                    st.success(f"<i class='fas fa-check-circle fa-icon'></i> Successfully logged R {amount:,.2f} for {category}")
                except Exception as e:
                    st.error(f"Error logging expenditure: {e}")

    # 4. View History & Instant Verification
    st.divider()
    
    # Quick Summary Metric
    current_exps = database.get_df("SELECT SUM(amount) as total FROM expenditure_log WHERE project_id = ?", (project_id,))
    total_val = current_exps['total'].iloc[0] if not current_exps.empty and current_exps['total'].iloc[0] else 0.0
    st.metric(label="Total Recorded Expenditure (Current Project)", value=f"R {total_val:,.2f}")

    st.subheader("Full Transaction History")
    exps = database.get_df('''
        SELECT el.spend_date, el.category, el.amount, el.reference_id, el.description, u.full_name as recorded_by
        FROM expenditure_log el
        JOIN users u ON el.recorded_by = u.user_id
        WHERE el.project_id = ?
        ORDER BY el.exp_id DESC
    ''', (project_id,))
    
    if not exps.empty:
        st.dataframe(exps, use_container_width=True, hide_index=True)
    else:
        st.info("No expenditures have been recorded yet for this project.")

if __name__ == "__main__":
    record_exp_page()
