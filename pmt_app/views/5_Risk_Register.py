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
    <div style="background: linear-gradient(135deg, #0c4a6e 0%, #0ea5e9 100%); color: white; padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 1.5rem; box-shadow: 0 4px 12px rgba(12, 74, 110, 0.2);">
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
    with st.expander("➕ LOG NEW PROJECT RISK / ISSUE", expanded=False):
        st.markdown("""
            <div style="background: rgba(14, 165, 233, 0.05); padding: 1.5rem; border-radius: 12px; border: 1px dashed rgba(14, 165, 233, 0.3); margin-bottom: 1rem;">
                <div style="font-weight: 600; color: #38bdf8; font-size: 1.1rem; margin-bottom: 0.5rem;">Risk Identification</div>
                <div style="font-size: 0.85rem; opacity: 0.8;">Fill in the details below to log a new risk or issue. Linking it to an activity ensures the right team member is notified.</div>
            </div>
        """, unsafe_allow_html=True)

        # Fetch activities for linkage
        activities = database.get_baseline_schedule(project_id)
        activity_map = {"--- Project Level (No Specific Activity) ---": None}
        if not activities.empty:
            for _, act in activities.iterrows():
                activity_map[f"{act['activity_name']} (Responsible: {act['responsible_name']})"] = act['activity_id']
        
        with st.form("add_risk_form", clear_on_submit=True):
            # Row 1: Description
            st.markdown('<div style="margin-bottom: -10px; font-size: 0.8rem; font-weight: 600; color: #94a3b8;">WHAT IS THE RISK?</div>', unsafe_allow_html=True)
            r_desc = st.text_input("Description", placeholder="e.g., Delay in equipment delivery from vendor", label_visibility="collapsed")
            
            # Row 2: Linkage & Impact
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.markdown('<div style="margin-bottom: 5px; font-size: 0.8rem; font-weight: 600; color: #94a3b8;"><i class="fas fa-link"></i> LINKED ACTIVITY</div>', unsafe_allow_html=True)
                r_activity = st.selectbox("Activity", list(activity_map.keys()), label_visibility="collapsed")
            with c2:
                st.markdown('<div style="margin-bottom: 5px; font-size: 0.8rem; font-weight: 600; color: #94a3b8;"><i class="fas fa-exclamation-circle"></i> IMPACT</div>', unsafe_allow_html=True)
                r_impact = st.selectbox("Impact", ["H", "M", "L"], index=1, label_visibility="collapsed")
            with c3:
                st.markdown('<div style="margin-bottom: 5px; font-size: 0.8rem; font-weight: 600; color: #94a3b8;"><i class="fas fa-calendar-day"></i> DATE</div>', unsafe_allow_html=True)
                r_date = st.date_input("Identified Date", value=datetime.today(), label_visibility="collapsed")
            
            # Row 3: Mitigation
            st.markdown('<div style="margin-top: 10px; margin-bottom: 5px; font-size: 0.8rem; font-weight: 600; color: #94a3b8;"><i class="fas fa-shield-alt"></i> MITIGATION PLAN</div>', unsafe_allow_html=True)
            r_mitigation = st.text_area("Plan", placeholder="What actions are being taken to minimize this risk?", label_visibility="collapsed", height=100)
            
            # Submit Button
            st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
            col_btn_s1, col_btn, col_btn_s2 = st.columns([1, 1, 1])
            with col_btn:
                st.markdown('<div class="add-btn">', unsafe_allow_html=True)
                submitted = st.form_submit_button("REGISTER RISK", use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            if submitted:
                if not r_desc:
                    st.error("Please provide a risk description.")
                else:
                    new_risk_data = {
                        'project_id': project_id,
                        'activity_id': activity_map[r_activity],
                        'description': r_desc,
                        'impact': r_impact,
                        'date_identified': r_date,
                        'mitigation_action': r_mitigation,
                        'status': 'Open'
                    }
                    database.add_risk(new_risk_data, current_user['id'])
                    st.success("✅ Risk registered and assigned successfully!")
                    st.rerun()

    # --- Resolve Risk Dialog ---
    @st.dialog("Resolve Risk", width="medium")
    def resolve_risk_dialog(risk_id, risk_desc):
        st.markdown(f"### Resolving Risk: **{risk_desc}**")
        st.info("To resolve this risk, you must upload document(s) proving the mitigation action was successful.")
        
        uploaded_files = st.file_uploader(
            "Upload Closure Proof(s) *",
            type=['pdf', 'docx', 'xlsx', 'png', 'jpg', 'jpeg', 'zip'],
            accept_multiple_files=True,
            key=f"close_{risk_id}"
        )
        
        if uploaded_files:
            st.success(f"📂 {len(uploaded_files)} file(s) selected.")
            if st.button("✅ Confirm Resolution", type="primary", use_container_width=True):
                saved_paths = []
                for uploaded_file in uploaded_files:
                    # Determine blob name
                    blob_name = f"uploads/risks/{risk_id}/{uploaded_file.name}"
                    # Upload to Azure
                    database.upload_file_to_azure(uploaded_file.getvalue(), blob_name)
                    saved_paths.append(blob_name)
                
                # Update DB with comma-separated paths
                paths_str = ",".join(saved_paths)
                database.update_risk_status(risk_id, "Resolved", current_user['id'], closure_file_path=paths_str)
                st.success(f"Risk resolved and {len(uploaded_files)} proof(s) uploaded to Cloud!")
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
                    link_info = f"🔗 Linked to: {risk['activity_name']}" if risk['activity_name'] else "🌍 Project Level"
                    st.caption(f"📅 {risk['date_identified']} | {link_info}")
                    st.caption(f"Plan: {risk['mitigation_action']}")
                with rc2:
                    color = "red" if risk['impact'] == 'H' else ("orange" if risk['impact'] == 'M' else "blue")
                    st.markdown(f":{color}[**{risk['impact']}-Impact**]")
                with rc3:
                    st.markdown('<div class="check-btn">', unsafe_allow_html=True)
                    if st.button("Resolve", key=f"close_risk_{risk['risk_id']}", type="primary", use_container_width=True):
                        resolve_risk_dialog(risk['risk_id'], risk['description'])
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
