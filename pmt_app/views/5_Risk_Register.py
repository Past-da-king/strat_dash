import streamlit as st
import auth
import database
import pandas as pd
from datetime import datetime
import styles

# Page Config
st.set_page_config(page_title="PM Tool - Risk Register", layout="wide")

def risk_register_page():
    auth.require_role(['team', 'pm', 'admin', 'executive'])
    styles.global_css()
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #2c5aa0 0%, #5fa2e8 100%); color: white; padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 1.5rem; box-shadow: 0 4px 12px rgba(44, 90, 160, 0.2);">
        <div style="display: flex; align-items: center; gap: 12px;">
            <i class="fas fa-exclamation-triangle" style="font-size: 1.6rem;"></i>
            <div style="font-size: 1.6rem; font-weight: 700;">Risk Register</div>
        </div>
        <div style="font-size: 0.85rem; opacity: 0.9; margin-left: 36px;">Log new risks and manage existing ones</div>
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
    
    selected_project_str = st.selectbox("Select Project to Manage Risks", project_list)
    project_id = project_map[selected_project_str]
    
    st.divider()

    # A. Add New Risk Form
    with st.expander("Log New Risk / Issue", expanded=True):
        col_s1, col_center, col_s2 = st.columns([1, 2, 1])
        with col_center:
            with st.form("add_risk_form"):
                r_desc = st.text_input("Risk/Issue Description")
                c1, c2 = st.columns(2)
                with c1:
                    r_impact = st.selectbox("Impact Level", ["H", "M", "L"])
                with c2:
                    r_date = st.date_input("Date Identified", value=datetime.today())
                
                r_mitigation = st.text_area("Mitigation Plan")
                
                st.markdown('<div class="add-btn">', unsafe_allow_html=True)
                submitted = st.form_submit_button("Log Risk", use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                if submitted and r_desc:
                    new_risk_data = {
                        'project_id': project_id,
                        'description': r_desc,
                        'impact': r_impact,
                        'date_identified': r_date,
                        'mitigation_action': r_mitigation,
                        'status': 'Open'
                    }
                    database.add_risk(new_risk_data, current_user['id'])
                    st.success("Risk logged successfully!")
                    st.rerun()

    st.markdown("### Open Risks")
    
    # B. List & Close Risks
    risks = database.get_project_risks(project_id)
    open_risks = risks[risks['status'] == 'Open'] if not risks.empty else pd.DataFrame()
    
    if not open_risks.empty:
        for _, risk in open_risks.iterrows():
            with st.container(border=True):
                rc1, rc2, rc3 = st.columns([4, 1, 1])
                with rc1:
                    st.markdown(f"**{risk['description']}**")
                    st.caption(f"📅 {risk['date_identified']} | Plan: {risk['mitigation_action']}")
                with rc2:
                    color = "red" if risk['impact'] == 'H' else ("orange" if risk['impact'] == 'M' else "blue")
                    st.markdown(f":{color}[**{risk['impact']}-Impact**]")
                with rc3:
                    st.markdown('<div class="check-btn">', unsafe_allow_html=True)
                    if st.button("Resolve", key=f"close_risk_{risk['risk_id']}", type="primary", use_container_width=True):
                        database.update_risk_status(risk['risk_id'], "Resolved", current_user['id'])
                        st.success("Risk resolved.")
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("✅ No active open risks.")

    # Show History
    st.divider()
    with st.expander("View Resolved Risks"):
        resolved_risks = risks[risks['status'] != 'Open'] if not risks.empty else pd.DataFrame()
        if not resolved_risks.empty:
            st.dataframe(
                resolved_risks[['date_identified', 'description', 'impact', 'status', 'mitigation_action']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.caption("No resolved risks yet.")

if __name__ == "__main__":
    risk_register_page()
