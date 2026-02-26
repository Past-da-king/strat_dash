import streamlit as st
import auth
import database
import pandas as pd
import base64
import styles

# Page Config
st.set_page_config(page_title="PM Tool - Project Repository", layout="wide")


def project_repository_page():
    auth.require_role(['team', 'pm', 'admin', 'executive'])
    styles.global_css()

    # --- HEADER ---
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0c4a6e 0%, #0ea5e9 100%); color: white; padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 1.5rem; box-shadow: 0 4px 12px rgba(12, 74, 110, 0.2);">
        <div style="display: flex; align-items: center; gap: 12px;">
            <i class="fas fa-network-wired" style="font-size: 1.6rem;"></i>
            <div style="font-size: 1.6rem; font-weight: 700;">Knowledge Repository</div>
        </div>
        <div style="font-size: 0.85rem; opacity: 0.9; margin-left: 36px;">Manage project documentation and file relationships</div>
    </div>
    """, unsafe_allow_html=True)

    # --- STYLING ---
    st.markdown("""<style>
        .file-row { display: flex; align-items: center; padding: 12px; border-bottom: 1px solid rgba(128,128,128,0.1); border-radius: 6px; transition: background 0.2s; }
        .file-row:hover { background: rgba(14, 165, 233, 0.05); }
        .file-icon { width: 32px; display: flex; justify-content: center; }
        .file-name { flex: 1; font-weight: 500; cursor: pointer; color: #0ea5e9; margin-left:12px; }
        .file-meta { font-size: 0.75rem; color: #94a3b8; text-align: right; min-width: 180px; }
        .related-pill { background: rgba(14, 165, 233, 0.1); color: #0ea5e9; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; font-weight: 600; margin-left: 6px; }
        .fa-folder { color: #f59e0b; }
        .fa-file-pdf { color: #ef4444; }
        .fa-file-excel { color: #10b981; }
        /* VIOLENT VERTICAL REDUCTION */
        .repo-table-row, .repo-table-row * {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            min-height: 0 !important;
            line-height: 1.0 !important;
        }
        [data-testid="stVerticalBlock"] { gap: 0 !important; }
        
        .repo-table-row [data-testid="column"] {
            display: flex !important;
            align-items: center !important;
            height: 30px !important;
        }

        /* NUCLEAR RESET for buttons */
        [data-testid="stButton"] button, 
        [data-testid="stPopover"] button {
            border: none !important;
            background: transparent !important;
            background-color: transparent !important;
            box-shadow: none !important;
            padding: 0 !important;
            min-height: unset !important;
            width: auto !important;
            outline: none !important;
            display: flex !important;
            align-items: center !important;
        }

        /* The Ellipsis character */
        div[data-testid="stPopover"] [data-testid="stMarkdownContainer"] p {
            font-size: 1.4rem !important;
            font-weight: 900 !important;
            color: #94a3b8 !important;
            margin: 0 !important;
        }

        /* KILL ALL ARROWS and SVG artifacts */
        [data-testid="stPopover"] svg, 
        [data-testid="stIconChevronDown"] {
            display: none !important;
            width: 0 !important;
            height: 0 !important;
            visibility: hidden !important;
            position: absolute !important;
        }
        
        /* Folder Links: Plain URLs */
        .folder-link-row [data-testid="stButton"] button {
            color: #0ea5e9 !important;
            font-weight: 500 !important;
            font-size: 0.95rem !important;
            text-decoration: none !important;
        }
        .folder-link-row [data-testid="stButton"] button:hover {
            color: #38bdf8 !important;
            text-decoration: underline !important;
        }
    </style>""", unsafe_allow_html=True)

    # --- PROJECT SELECTION ---
    current_user = auth.get_current_user()
    is_global_role = current_user['role'] in ['admin', 'executive', 'team']
    user_id_filter = None if is_global_role else current_user['id']
    projects = database.get_projects(user_id=user_id_filter)

    if projects.empty:
        st.info("No projects assigned to you found.")
        st.stop()

    prj_options = {f"{r['project_number']} - {r['project_name']}": r['project_id'] for _, r in projects.iterrows()}
    project_id = prj_options[st.selectbox("Active Project", list(prj_options.keys()))]

    st.divider()

    # --- CORE REPO TABS ---
    # Removed Query Param-based Action Handlers to prevent Streamlit Cloud Logouts
    # --- CORE REPO TABS ---
    # Clean text-based tabs as requested
    tab_repo, tab_act, tab_risk = st.tabs(["Global Repository", "Activity Outputs", "Risk Closure Proofs"])
    
    # Custom CSS for UI refinements
    st.markdown("""<style>
        .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
            display: flex; align-items: center; gap: 8px; font-weight: 600;
        }

        .conn-header { font-size: 0.7rem; font-weight: 700; color: #475569; margin: 12px 0 4px 0; letter-spacing: 0.05em; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px; }
    </style>""", unsafe_allow_html=True)

    # =========================================================================
    # HELPERS
    # =========================================================================
    def get_icon(filename, is_folder=False):
        if is_folder: return '<i class="fas fa-folder" style="color: #f59e0b;"></i>'
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext == 'pdf': return '<i class="fas fa-file-pdf" style="color: #ef4444;"></i>'
        if ext in ['xlsx', 'xls', 'csv']: return '<i class="fas fa-file-excel" style="color: #10b981;"></i>'
        if ext in ['docx', 'doc']: return '<i class="fas fa-file-word" style="color: #0ea5e9;"></i>'
        return '<i class="fas fa-file-alt" style="color: #94a3b8;"></i>'

    def make_download_link(data_bytes, filename, label="Download"):
        """Generate a plain HTML <a> download link from raw bytes. No button."""
        b64 = base64.b64encode(data_bytes).decode()
        return f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">{label}</a>'

    def render_linked_context(item_type, item_id):
        """Render automated and manual links as a knowledge graph context."""
        # 1. Manual Links
        links = database.get_file_links(item_type, item_id)
        if links:
            st.markdown("<div class='conn-header'>CONNECTIONS</div>", unsafe_allow_html=True)
            for l in links:
                if l['source_type'] == item_type and l['source_id'] == item_id:
                    other_type, other_id = l['target_type'], l['target_id']
                else:
                    other_type, other_id = l['source_type'], l['source_id']
                
                type_map = {'R': 'Repo', 'A': 'Activity', 'K': 'Risk'}
                st.caption(f"↳ {type_map.get(other_type)} #{other_id}")
        
        # 2. Create Link UI
        with st.expander("Link to another document..."):
            target_type = st.selectbox("Type", ["R", "A", "K"], key=f"lt_{item_type}_{item_id}")
            target_id = st.number_input("ID", min_value=1, key=f"li_{item_type}_{item_id}")
            if st.button("Create Link", key=f"lb_{item_type}_{item_id}"):
                database.create_file_link(item_type, item_id, target_type, target_id, current_user['id'])
                st.rerun()

    # =========================================================================
    # TAB 1: GLOBAL REPOSITORY (Manual Hierarchy)
    # =========================================================================
    with tab_repo:
        nav_key = f"repo_nav_{project_id}"
        if nav_key not in st.session_state: st.session_state[nav_key] = [{'id': None, 'name': 'ROOT'}]
        
        current_nav = st.session_state[nav_key]
        current_folder = current_nav[-1]['id']

        # --- REPO HEADER BAR ---
        head_col1, head_col2 = st.columns([8, 2])
        with head_col1:
            # Simple breadcrumbs
            bc_links = []
            for i, n in enumerate(current_nav):
                bc_links.append(f"<span style='color:#0ea5e9;'>{n['name']}</span>")
            bc_str = " <span style='color:#475569;'>/</span> ".join(bc_links)
            st.markdown(f'<div style="display:flex; align-items:center; gap:8px; font-size:0.95rem; margin-bottom:15px; color:#64748b;">{bc_str}</div>', unsafe_allow_html=True)
        
        with head_col2:
            # Minimalist Action Bar
            h_c1, h_c2 = st.columns(2)
            with h_c1:
                if len(current_nav) > 1:
                    if st.button("", icon=":material/north_west:", help="Level Up", key="btn_up"):
                        st.session_state[nav_key].pop()
                        st.rerun()
            with h_c2:
                with st.popover("", icon=":material/create_new_folder:", help="New...", use_container_width=True):
                    st.markdown("##### New...")
                    s_t1, s_t2 = st.tabs(["Folder", "File"])
                    with s_t1:
                        f_name = st.text_input("Name", key="f_n_input")
                        if st.button("Create", use_container_width=True):
                            database.create_repo_folder(project_id, f_name, current_folder, current_user['id'])
                            st.rerun()
                    with s_t2:
                        files = st.file_uploader("Select", accept_multiple_files=True, key="f_u_input")
                        if files and st.button("Upload", use_container_width=True):
                            for f in files:
                                blob = f"uploads/projects/{project_id}/repo/{f.name}"
                                database.upload_file_to_azure(f.getvalue(), blob)
                                database.add_repo_file(project_id, current_folder, f.name, blob, current_user['id'])
                            st.rerun()

        st.divider()
        
        # --- FILE LISTING ---
        # --- FILE LISTING HEADERS ---
        h1, h2, h3, h4, h5 = st.columns([0.4, 5.1, 2, 2, 0.5])
        with h2: st.markdown("<span style='font-size:0.8rem; font-weight:700; color:#475569;'>Name</span>", unsafe_allow_html=True)
        with h3: st.markdown("<span style='font-size:0.8rem; font-weight:700; color:#475569;'>Date modified</span>", unsafe_allow_html=True)
        with h4: st.markdown("<span style='font-size:0.8rem; font-weight:700; color:#475569;'>Uploaded by</span>", unsafe_allow_html=True)
        st.markdown('<div style="height:1px; background:rgba(128,128,128,0.2); width:100%; margin:4px 0 12px 0;"></div>', unsafe_allow_html=True)

        contents = database.get_repo_contents(project_id, parent_id=current_folder)
        if contents.empty:
            st.info("This folder is empty.")
        else:
            for _, item in contents.iterrows():
                # Table Row Layout with specific class for alignment
                st.markdown('<div class="repo-table-row">', unsafe_allow_html=True)
                with st.container():
                    r1, r2, r3, r4, r5 = st.columns([0.4, 5.1, 2, 2, 0.5])
                    
                    # 1. Icon
                    with r1: 
                        st.markdown(get_icon(item["name"], item["is_folder"]), unsafe_allow_html=True)
                    
                    # 2. Name
                    with r2:
                        if item['is_folder']:
                            st.markdown(f'<div class="folder-link-row">', unsafe_allow_html=True)
                            if st.button(item['name'], key=f"f_click_{item['file_id']}", help="Open"):
                                st.session_state[nav_key].append({'id': item['file_id'], 'name': item['name']})
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div style="font-weight:400; font-size:1.0rem;">{item["name"]}</div>', unsafe_allow_html=True)
                    
                    # 3. Date
                    with r3:
                        st.markdown(f'<div style="font-size:0.85rem; color:#64748b;">{str(item["created_at"])[:10]}</div>', unsafe_allow_html=True)
                    
                    # 4. Uploader
                    with r4:
                        st.markdown(f'<div style="font-size:0.85rem; color:#64748b;">{item["uploader_name"]}</div>', unsafe_allow_html=True)
                    
                    # 5. Options (Three Dots)
                    with r5:
                        with st.popover("⋮", icon=None, help="Actions"):
                            if not item['is_folder']:
                                try:
                                    data = database.download_file_from_azure(item['file_path'])
                                    st.markdown(make_download_link(data, item['name'], "Download Permanent"), unsafe_allow_html=True)
                                except: st.caption("File missing")
                            
                            # Delete Action (Styled proper button)
                            st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
                            if st.button("Delete Permanent", key=f"del_repo_{item['file_id']}", use_container_width=True):
                                database.delete_repo_item(item['file_id'])
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
                            render_linked_context('R', item['file_id'])
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Invisible row separator
                st.markdown('<div style="height:1px; background:rgba(128,128,128,0.05); width:100%; margin:2px 0;"></div>', unsafe_allow_html=True)

    # =========================================================================
    # TAB 2: ACTIVITY OUTPUTS (Automated)
    # =========================================================================
    with tab_act:
        activities = database.get_baseline_schedule(project_id)
        if activities.empty: st.info("No activities recorded.")
        else:
            for _, act in activities.iterrows():
                outputs = database.get_task_outputs(act['activity_id'])
                if outputs.empty: continue
                
                with st.expander(f"Task: {act['activity_name']}", expanded=True):
                    for _, out in outputs.iterrows():
                        ar1, ar2, ar3 = st.columns([0.4, 8.6, 1])
                        with ar1: st.markdown(f'<div style="margin-top: 5px;">{get_icon(out["file_name"])}</div>', unsafe_allow_html=True)
                        with ar2:
                            st.markdown(f"**{out['file_name']}**")
                            st.caption(f"Uploaded by {out['uploader_name']} on {str(out['uploaded_at'])[:10]}")
                        with ar3:
                            with st.popover("⋮", icon=None, help="Options", use_container_width=True):
                                try:
                                    data = database.download_file_from_azure(out['file_path'])
                                    st.markdown(make_download_link(data, out['file_name'], "Download Permanent"), unsafe_allow_html=True)
                                except: st.caption("File missing")
                                
                                # Delete Action (Styled proper button)
                                st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
                                if st.button("Delete Permanent", key=f"del_act_{out['output_id']}", use_container_width=True):
                                    database.delete_task_output(out['output_id'])
                                    st.rerun()
                                st.markdown('</div>', unsafe_allow_html=True)
                                render_linked_context('A', out['output_id'])

    # =========================================================================
    # TAB 3: RISK PROOFS (Automated - Files Only)
    # =========================================================================
    with tab_risk:
        risks = database.get_project_risks(project_id)
        proofed_risks = risks[risks['closure_file_path'].notnull()]
        
        if proofed_risks.empty: st.info("No risk closure files uploaded yet.")
        else:
            for _, r in proofed_risks.iterrows():
                with st.expander(f"Proof for: {r['description'][:50]}...", expanded=True):
                    paths = r['closure_file_path'].split(',')
                    for p in paths:
                        p = p.strip()
                        if not p: continue
                        fname = p.rsplit('/', 1)[-1]
                        kr1, kr2, kr3 = st.columns([0.4, 8.6, 1])
                        with kr1: st.markdown(f'<div style="margin-top: 5px;">{get_icon(fname)}</div>', unsafe_allow_html=True)
                        with kr2:
                            st.markdown(f"**{fname}**")
                            if r['activity_id']:
                                st.markdown(f'<div style="font-size: 0.7rem; color: #38bdf8;"><i class="fas fa-link"></i> Task: {r["activity_name"]}</div>', unsafe_allow_html=True)
                        with kr3:
                            with st.popover("⋮", icon=None, help="Options", use_container_width=True):
                                try:
                                    data = database.download_file_from_azure(p)
                                    st.markdown(make_download_link(data, fname, "Download Permanent"), unsafe_allow_html=True)
                                except: st.caption("File missing")
                                
                                # Delete Action (Styled proper button)
                                st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
                                if st.button("Delete Permanent", key=f"del_risk_{r['risk_id']}_{hash(p)}", use_container_width=True):
                                    database.remove_risk_closure_file(r['risk_id'], p)
                                    st.rerun()
                                st.markdown('</div>', unsafe_allow_html=True)
                                render_linked_context('K', r['risk_id'])



if __name__ == "__main__":
    project_repository_page()

