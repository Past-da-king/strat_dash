import streamlit as st
import auth
import database
import calculations
import pandas as pd
import os
import styles
import pdf_generator

# Page Config
st.set_page_config(page_title="PM Tool - Executive Dashboard", layout="wide")

def executive_dashboard():
    auth.require_role(['admin', 'executive'])
    styles.global_css()
    
    # --- Sidebar Controls ---
    with st.sidebar:
        st.header("Dashboard Controls")
        st.markdown('<div class="refresh-btn">', unsafe_allow_html=True)
        if st.button("Refresh Data", use_container_width=True, type="primary"):
            st.cache_data.clear()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- Header ---
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0c4a6e 0%, #0ea5e9 100%); color: white; padding: 2rem; border-radius: 12px; margin-bottom: 2rem; box-shadow: 0 4px 12px rgba(12, 74, 110, 0.2);">
        <div style="display: flex; align-items: center; gap: 15px;">
            <i class="fas fa-chart-pie" style="font-size: 2.2rem;"></i>
            <div style="font-size: 2.2rem; font-weight: 700; letter-spacing: -0.5px;">PORTFOLIO OVERVIEW</div>
        </div>
        <div style="font-size: 0.95rem; opacity: 0.9; margin-top: 0.5rem; margin-left: 50px;">Strategic Project Performance Portal</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Get all projects
    projects = database.get_projects(pm_id=None)
    
    if projects.empty:
        st.info("No projects found in the system.")
        st.stop()
    
    # --- Portfolio Summary Metrics ---
    total_projects = len(projects)
    total_budget = pd.to_numeric(projects['total_budget'], errors='coerce').sum() if 'total_budget' in projects.columns else 0
    
    # Gather metrics for all projects
    all_metrics = []
    for _, proj in projects.iterrows():
        m = calculations.get_project_metrics(proj['project_id'])
        if m:
            all_metrics.append(m)
    
    total_spent = sum(m['total_spent'] for m in all_metrics) if all_metrics else 0
    avg_completion = sum(m['pct_complete'] for m in all_metrics) / len(all_metrics) if all_metrics else 0
    
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Total Projects", total_projects)
    s2.metric("Portfolio Budget", f"R {total_budget:,.0f}")
    s3.metric("Total Spent", f"R {total_spent:,.0f}")
    s4.metric("Avg Completion", f"{avg_completion:.1f}%")
    
    st.markdown("---")
    
    # --- Project Cards ---
    st.subheader("Project Detail Cards")
    
    cols_per_row = 2
    for i in range(0, len(all_metrics), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(all_metrics):
                break
            m = all_metrics[idx]
            
            with col:
                # Health color mapping
                health_color = "#4caf50" if m['budget_health'] == 'Green' else ("#ffc107" if m['budget_health'] == 'Yellow' else "#f44336")
                status_icon = "check-circle" if m['budget_health'] == 'Green' else ("exclamation-triangle" if m['budget_health'] == 'Yellow' else "times-circle")
                pct = min(m['pct_complete'], 100)
                
                # Premium Card HTML
                st.markdown(f"""
                <div class="project-card">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div>
                            <div class="project-card-title">{m['project_name']}</div>
                            <div class="project-card-meta">{m['project_number']} | Client: {m.get('client', 'N/A')}</div>
                        </div>
                        <span style="background:{health_color}22; color:{health_color}; border: 1px solid {health_color}44; padding:4px 12px; border-radius:20px; font-size:0.7rem; font-weight:700; display:flex; align-items:center; gap:5px;">
                            <i class="fas fa-{status_icon}"></i> {m['budget_health'].upper()}
                        </span>
                    </div>
                    <div class="metric-grid">
                        <div class="metric-box">
                            <div class="metric-box-label">Budget</div>
                            <div class="metric-box-value">R {m['total_budget']:,.0f}</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-box-label">Spent</div>
                            <div class="metric-box-value">R {m['total_spent']:,.0f}</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-box-label">Complete</div>
                            <div class="metric-box-value">{m['pct_complete']:.1f}%</div>
                        </div>
                    </div>
                    <div class="progress-container">
                        <div class="progress-fill" style="width:{pct}%"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Action buttons positioned below the custom card (Streamlit Native for functionality)
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    st.markdown('<div class="pm-btn">', unsafe_allow_html=True)
                    if st.button("Dashboard", key=f"view_{m['project_id']}", use_container_width=True):
                        st.session_state['selected_project'] = m['project_number']
                        st.switch_page("views/2_PM_Dashboard.py")
                    st.markdown('</div>', unsafe_allow_html=True)
                with btn_col2:
                    st.markdown('<div class="report-btn">', unsafe_allow_html=True) 
                    if st.button("Report", key=f"pdf_{m['project_id']}", use_container_width=True):
                        try:
                            pdf_gen = pdf_generator.PDFReportGenerator(m['project_id'])
                            pdf_bytes = pdf_gen.generate()
                            st.markdown('<div class="download-btn">', unsafe_allow_html=True)
                            st.download_button(
                                "Download",
                                data=pdf_bytes,
                                file_name=f"Report_{m['project_number']}.pdf",
                                mime="application/pdf",
                                key=f"dl_pdf_{m['project_id']}",
                                use_container_width=True
                            )
                            st.markdown('</div>', unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"Error: {e}")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('<div style="margin-bottom:2rem;"></div>', unsafe_allow_html=True)

if __name__ == "__main__":
    executive_dashboard()
