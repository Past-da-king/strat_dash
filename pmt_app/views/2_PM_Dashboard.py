import streamlit as st
import auth
import database
import calculations
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import styles
import pdf_generator

# Page Config
st.set_page_config(
    page_title="PM Tool - Project Dashboard", 
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def pm_dashboard():
    auth.require_role(['pm', 'admin', 'executive'])
    
    # Apply Global Styles
    styles.global_css()
    
    # --- BRAND COLORS ---
    COLORS = {
        'status_not_started': '#f59e0b',
        'status_active': '#10b981',
        'status_complete': '#0ea5e9',
        'status_critical': '#ef4444',
        'fin_budget': '#1e293b',
        'fin_actual': '#0891b2',
        'fin_forecast': '#7c3aed',
        'cat_labour': '#db2777',
        'cat_material': '#4f46e5',
        'cat_vehicle': '#ea580c',
        'cat_diesel': '#059669',
        'cat_other': '#94a3b8',
        'risk_high': '#f44336',
        'risk_medium': '#ff9800',
        'risk_low': '#4caf50',
        'text': 'inherit',
        'subtext': 'grey',
        'card_bg': 'rgba(255, 255, 255, 0.05)'
    }

    # --- CUSTOM CSS ---
    st.markdown("""
    <style>
        .report-header {
            background: linear-gradient(135deg, #2c5aa0 0%, #5fa2e8 100%);
            color: white !important;
            padding: 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            box-shadow: 0 4px 12px rgba(44, 90, 160, 0.2);
        }
        .report-title { 
            font-size: 2.2rem; font-weight: 700; margin: 0; 
            color: white !important; letter-spacing: -0.5px;
        }
        .report-date { 
            font-size: 0.95rem; opacity: 0.9; 
            color: white !important; margin-top: 0.5rem;
        }
        h3 { font-size: 1.25rem; font-weight: 600; margin-top: 1.5rem; margin-bottom: 1rem; }
        .kpi-card {
            background-color: var(--card-bg);
            border-left: 5px solid var(--primary-color);
            padding: 1.5rem; border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            text-align: center; transition: all 0.3s ease;
        }
        .kpi-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.12);
        }
        .kpi-value { font-size: 1.8rem; font-weight: 700; color: var(--primary-color) !important; }
        .kpi-label { font-size: 0.9rem; color: var(--subtext-color) !important; text-transform: uppercase; letter-spacing: 0.5px; }
        .summary-box {
            background-color: var(--card-bg); color: inherit;
            padding: 2rem; border-radius: 12px;
            border: 1px solid rgba(128, 128, 128, 0.1); margin-bottom: 1rem;
            box-shadow: 0 4px 10px rgba(0,0,0,0.03); line-height: 1.8; min-height: 140px;
        }
        .health-container {
            display: flex; justify-content: space-around; align-items: center;
            padding: 2rem 0; background: var(--card-bg); border-radius: 12px;
            border: 1px solid rgba(128, 128, 128, 0.1); box-shadow: 0 4px 10px rgba(0,0,0,0.03); min-height: 160px;
        }
        .deliverable-row {
            display: flex; justify-content: space-between; align-items: center;
            border-bottom: 1px solid rgba(128, 128, 128, 0.1); padding: 12px 0;
        }
        .badge-sm {
            display: inline-block; padding: 2px 8px; border-radius: 12px;
            font-size: 0.7rem; font-weight: 600;
        }
        .badge-user { background: #eff6ff !important; color: #2c5aa0 !important; }
        .badge-output { background: #fefce8 !important; color: #a16207 !important; }
        .badge-status { background: #dbeafe !important; color: #1e40af !important; }
    </style>
    """, unsafe_allow_html=True)

    # --- PROJECT SELECTION ---
    current_user = auth.get_current_user()
    is_global_role = current_user['role'] in ['admin', 'executive']
    pm_id_filter = None if is_global_role else current_user['id']
    projects = database.get_projects(pm_id=pm_id_filter)
    
    if projects.empty:
        st.info("No projects assigned to you found.")
        st.stop()
        
    project_map = {f"{row['project_number']} - {row['project_name']}": row['project_id'] 
                   for _, row in projects.iterrows()}
    project_list = list(project_map.keys())
    
    selected_num = st.session_state.get('selected_project')
    default_idx = 0
    if selected_num:
        matches = [i for i, s in enumerate(project_list) if selected_num in s]
        if matches: default_idx = matches[0]

    with st.sidebar:
        st.header("Dashboard Controls")
        st.markdown('<div class="refresh-btn">', unsafe_allow_html=True)
        if st.button("Refresh Data", use_container_width=True, type="primary"):
            st.cache_data.clear()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        selected_project_str = st.selectbox("Select Project", project_list, index=default_idx)
        
        project_id = project_map[selected_project_str]
        st.markdown("### Reports")
        st.markdown('<div class="report-btn">', unsafe_allow_html=True)
        if st.button("Generate PDF Report", use_container_width=True):
            with st.spinner("Generating PDF..."):
                try:
                    pdf_gen = pdf_generator.PDFReportGenerator(project_id)
                    pdf_bytes = pdf_gen.generate()
                    st.markdown('<div class="download-btn">', unsafe_allow_html=True)
                    st.download_button(
                        label="Download PDF", data=pdf_bytes,
                        file_name=f"Project_Status_{project_id}.pdf",
                        mime="application/pdf", use_container_width=True
                    )
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.success("Report generated!")
                except Exception as e:
                    st.error(f"Failed to generate PDF: {e}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Metrics
    m = calculations.get_project_metrics(project_id)
    if not m:
        st.error("Project details could not be retrieved.")
        st.stop()

    # --- HEADER ---
    st.markdown(f"""
    <div class="report-header" style="background: linear-gradient(135deg, #0c4a6e 0%, #0ea5e9 100%);">
        <div style="display: flex; align-items: center; gap: 15px;">
            <i class="fas fa-file-invoice" style="font-size: 2.2rem;"></i>
            <div class="report-title">STRATEGIC STATUS REPORT</div>
        </div>
        <div class="report-date" style="margin-left: 50px;">{m['project_name']} ({m['project_number']}) | {pd.Timestamp.now().strftime('%B %d, %Y')}</div>
    </div>
    """, unsafe_allow_html=True)

    # --- EXECUTIVE SUMMARY & HEALTH ---
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### Executive Summary")
        status_text = "exceeding budget" if m['forecast'] > m['total_budget'] else "well within budget"
        formatted_pct = "{:.1f}%".format(m['pct_complete'])
        formatted_cost = "R {:,.2f}".format(m['forecast'])
        
        summary_html = f"""
        <div class="summary-box">
        <i class="fas fa-info-circle fa-icon"></i>
        The project <b>{m['project_name']}</b> is currently in <b>{m['actual_status']}</b> status. 
        Physical completion is estimated at <b>{formatted_pct}</b>. 
        Financial performance shows we are <b>{status_text}</b> with a forecasted completion cost of <b>{formatted_cost}</b>.
        </div>
        """
        st.markdown(summary_html, unsafe_allow_html=True)

    with col2:
        st.markdown("### Project Health")
        health_data = [
            ('Scope', COLORS['status_active'], '✓'),
            ('Schedule', 
             COLORS['status_active'] if m['schedule_health'] == 'Green' else COLORS['status_not_started'], 
             '✓' if m['schedule_health'] == 'Green' else '!'),
            ('Budget', 
             COLORS['status_active'] if m['budget_health'] == 'Green' else (COLORS['status_not_started'] if m['budget_health'] == 'Yellow' else COLORS['status_critical']), 
             '✓' if m['budget_health'] == 'Green' else '!'),
            ('Resources', COLORS['status_active'], '✓')
        ]
        
        health_html = '<div class="health-container">'
        for label, hex_color, icon in health_data:
            is_active = (hex_color == COLORS['status_active'] or hex_color == COLORS['status_complete'])
            text_color = "white" if is_active else hex_color
            border = "none" if is_active else f"3px solid {hex_color}"
            inner_bg = hex_color if is_active else "white"
            health_html += f"""<div class="health-item"><div class="health-icon" style="background-color: {inner_bg}; color: {text_color}; border: {border};">{icon}</div><div class="health-label">{label}</div></div>"""
        health_html += '</div>'
        st.markdown(health_html, unsafe_allow_html=True)

    st.markdown("---")

    # --- DIALOGS ---
    @st.dialog("Project Plan Details", width="large")
    def show_full_timeline(project_id, activities):
        if activities.empty:
            st.info("No activities to display.")
            return
        st.markdown("### Extended Project Schedule")
        activities['planned_start'] = pd.to_datetime(activities['planned_start'])
        activities['planned_finish'] = pd.to_datetime(activities['planned_finish'])
        activities = activities.sort_values('planned_start', ascending=False)
        
        fig = px.timeline(activities, x_start="planned_start", x_end="planned_finish", y="activity_name", 
                          color="status_mapped", 
                          color_discrete_map={
                              'Not Started': COLORS['status_not_started'], 
                              'Active': COLORS['status_active'], 
                              'Complete': COLORS['status_complete']
                          },
                          hover_data=["planned_start", "planned_finish", "budgeted_cost", "responsible_name", "expected_output"])
        fig.update_yaxes(title="")
        fig.update_layout(
            showlegend=True, legend=dict(orientation="h", y=-0.1),
            xaxis_title="", yaxis_title="",
            height=max(400, len(activities)*40),
            margin=dict(l=10, r=10, t=10, b=50),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=True, gridcolor='rgba(128, 128, 128, 0.1)')
        )
        st.plotly_chart(fig, use_container_width=True)

    @st.dialog("Detailed Financials & Drill-down", width="large")
    def show_full_financials(project_id):
        df = database.get_df('''
            SELECT spend_date, category, amount, reference_id, description 
            FROM expenditure_log WHERE project_id = %s ORDER BY spend_date DESC
        ''', (project_id,))
        if df.empty:
            st.info("No expenditure recorded for this project yet.")
            return
        st.markdown("### Transaction Explorer")
        categories = ["All"] + sorted(df['category'].unique().tolist())
        selected_cat = st.selectbox("Drill-down by Category:", categories)
        filtered_df = df if selected_cat == "All" else df[df['category'] == selected_cat]
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown(f"#### {selected_cat} Transactions")
            st.dataframe(filtered_df, use_container_width=True, hide_index=True)
        with c2:
            st.markdown("#### Summary Stats")
            cat_sum = filtered_df.groupby('category')['amount'].sum().reset_index()
            st.dataframe(cat_sum, use_container_width=True, hide_index=True)
            st.metric("Total in View", f"R {filtered_df['amount'].sum():,.2f}")
        st.divider()
        st.markdown("### Category Distribution")
        overall_cat = df.groupby('category')['amount'].sum().reset_index()
        fig_cat = px.bar(overall_cat, x='category', y='amount', color='category',
                        color_discrete_map={
                            'Labour': COLORS['cat_labour'], 'Material': COLORS['cat_material'],
                            'Vehicle': COLORS['cat_vehicle'], 'Diesel': COLORS['cat_diesel'],
                            'Other': COLORS['cat_other']
                        }, text_auto='.2s')
        fig_cat.update_layout(xaxis_title="", yaxis_title="Total Spend (R)", showlegend=False, height=350, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_cat, use_container_width=True)

    @st.dialog("Milestones Tracker", width="large")
    def show_full_milestones(milestones_df):
        st.markdown("### Project Phases & Milestones")
        display_cols = ['activity_name', 'planned_start', 'planned_finish', 'status', 'responsible_name', 'expected_output']
        available_cols = [c for c in display_cols if c in milestones_df.columns]
        st.dataframe(milestones_df[available_cols], use_container_width=True, hide_index=True)

    # --- ROW 1: SCHEDULE & KEY METRICS ---
    r1_col1, r1_col2 = st.columns([1, 1])
    
    with r1_col1:
        st.markdown("### Project Schedule")
        total_a = m['total_activities']
        comp = m['pct_complete']
        prog = (m['active_activities'] / total_a * 100) if total_a > 0 else 0.0
        not_s = max(0, 100 - comp - prog)
        
        sched_fig = go.Figure()
        stages = [
            ('Not started', not_s, COLORS['status_not_started']), 
            ('In progress', prog, COLORS['status_active']), 
            ('Complete', comp, COLORS['status_complete'])
        ]
        y_pos = 0
        for label, val, color in stages:
            sched_fig.add_shape(type="rect", x0=0, y0=y_pos+0.1, x1=100, y1=y_pos+0.6, fillcolor="#f5f7fa", line=dict(width=0), layer='below')
            sched_fig.add_shape(type="rect", x0=0, y0=y_pos+0.1, x1=val, y1=y_pos+0.6, fillcolor=color, line=dict(width=0), layer='above')
            sched_fig.add_annotation(x=-2, y=y_pos+0.35, text=label, xanchor="right", showarrow=False, font=dict(color="white", size=13))
            y_pos += 1.0
        sched_fig.update_layout(xaxis=dict(range=[-25, 105], visible=False), yaxis=dict(range=[-0.2, 3], visible=False), 
                                margin=dict(l=0, r=0, t=10, b=10), height=280, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(sched_fig, use_container_width=True, config={'displayModeBar': False})

    with r1_col2:
        st.markdown("### Key Metrics")
        k_col1, k_col2 = st.columns(2)
        with k_col1:
            st.markdown(f'<div class="kpi-card"><div class="kpi-value">R {m["total_budget"]:,.0f}</div><div class="kpi-label">Contract Budget</div></div>', unsafe_allow_html=True)
            st.markdown('<div style="height:15px"></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="kpi-card" style="border-left-color: {COLORS["fin_forecast"]};"><div class="kpi-value">{m["budget_used_pct"]:.1f}%</div><div class="kpi-label">Budget Used</div></div>', unsafe_allow_html=True)
        with k_col2:
            st.markdown(f'<div class="kpi-card" style="border-left-color: {COLORS["fin_actual"]};"><div class="kpi-value">R {m["total_spent"]:,.0f}</div><div class="kpi-label">Actual Costs</div></div>', unsafe_allow_html=True)
            st.markdown('<div style="height:15px"></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="kpi-card" style="border-left-color: {COLORS["status_active"]};"><div class="kpi-value">R {m["remaining"]:,.0f}</div><div class="kpi-label">Remaining</div></div>', unsafe_allow_html=True)

    st.markdown('<div style="height:30px"></div>', unsafe_allow_html=True)

    # --- ROW 2: FINANCIALS & COST BREAKDOWN ---
    r2_col1, r2_col2 = st.columns([1, 1])
    
    with r2_col1:
        col_fin_h, col_fin_b = st.columns([3, 1])
        with col_fin_h: st.markdown("### Financials")
        with col_fin_b: 
            st.markdown('<div class="chart-btn">', unsafe_allow_html=True)
            if st.button("Full View", key="btn_full_fin", use_container_width=True): show_full_financials(project_id)
            st.markdown('</div>', unsafe_allow_html=True)
        fin_fig = go.Figure()
        fin_items = [
            ('Forecast', m['forecast'], COLORS['fin_forecast']), 
            ('Actual', m['total_spent'], COLORS['fin_actual']), 
            ('Budget', m['total_budget'], COLORS['fin_budget'])
        ]
        max_v = max(m['total_budget'], m['forecast']) * 1.1 if max(m['total_budget'], m['forecast']) > 0 else 1000
        for i, (label, val, color) in enumerate(fin_items):
            fin_fig.add_trace(go.Bar(
                x=[val], y=[label], orientation='h', 
                marker=dict(color=color, cornerradius=4),
                text=[f"R {val:,.0f}"], textposition="auto", 
                textfont=dict(color='white', size=11),
                hovertemplate=f"<b>{label}</b>: R %{{x:,.0f}}<extra></extra>"
            ))
        fin_fig.update_layout(
            xaxis=dict(visible=False, range=[0, max_v*1.2]), 
            yaxis=dict(showgrid=False, tickfont=dict(family="Segoe UI", size=12)),
            margin=dict(l=0, r=0, t=0, b=0), height=200, 
            paper_bgcolor='rgba(0,0,0,0)', showlegend=False, bargap=0.3
        )
        st.plotly_chart(fin_fig, use_container_width=True, config={'displayModeBar': False})

    with r2_col2:
        st.markdown("### Cost Breakdown")
        exp_df = database.get_df("SELECT category, SUM(amount) as total FROM expenditure_log WHERE project_id = %s GROUP BY category", (project_id,))
        if not exp_df.empty:
            cost_fig = px.pie(exp_df, values='total', names='category', hole=0.7,
                             color='category',
                             color_discrete_map={
                                'Labour': COLORS['cat_labour'], 'Material': COLORS['cat_material'],
                                'Vehicle': COLORS['cat_vehicle'], 'Diesel': COLORS['cat_diesel'],
                                'Other': COLORS['cat_other']
                             })
            cost_fig.update_traces(textinfo='none')
            cost_fig.update_layout(
                showlegend=True, legend=dict(orientation="h", y=-0.1), 
                margin=dict(l=0, r=0, t=10, b=0), height=240, paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(cost_fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("No expenditure recorded.")

    st.markdown('<div style="height:30px"></div>', unsafe_allow_html=True)

    # Fetch Activities
    all_activities = database.get_df('''
        SELECT bs.*, 
               u.full_name as responsible_name,
               (CASE WHEN bs.status = 'Complete' THEN 'Complete' 
                     WHEN bs.status = 'Active' THEN 'Active' 
                     ELSE 'Not Started' END) as status_mapped,
               (CASE WHEN bs.status = 'Complete' THEN 1 ELSE 0 END) as is_finished,
               (CASE WHEN bs.status IN ('Active', 'Complete') THEN 1 ELSE 0 END) as is_started
        FROM baseline_schedule bs
        LEFT JOIN users u ON bs.responsible_user_id = u.user_id
        WHERE bs.project_id = %s ORDER BY bs.planned_start
    ''', (project_id,))

    # --- ROW 3: TIMELINE & MILESTONES ---
    r3_col1, r3_col2 = st.columns([1, 1])

    with r3_col1:
        col_tl_h, col_tl_b = st.columns([3, 1])
        with col_tl_h: st.markdown("### Project Timeline")
        with col_tl_b:
            st.markdown('<div class="list-btn">', unsafe_allow_html=True)
            if st.button("View Details", key="btn_full_tl", use_container_width=True): show_full_timeline(project_id, all_activities)
            st.markdown('</div>', unsafe_allow_html=True)
        
        if not all_activities.empty:
            dash_filter = all_activities[all_activities['status_mapped'].isin(['Active', 'Not Started'])]
            dash_filter['planned_start'] = pd.to_datetime(dash_filter['planned_start'])
            dash_view = dash_filter.sort_values('planned_start', ascending=False).tail(4) 
            dash_view = dash_view.sort_values('planned_start', ascending=False)
            
            if not dash_view.empty:
                tl_fig = px.timeline(dash_view, x_start="planned_start", x_end="planned_finish", y="activity_name",
                                    color="status_mapped", 
                                    color_discrete_map={
                                        'Not Started': COLORS['status_not_started'], 
                                        'Active': COLORS['status_active'],
                                        'Complete': COLORS['status_complete']
                                    },
                                    category_orders={"status_mapped": ["Not Started", "Active", "Complete"]})
                tl_fig.update_yaxes(title="") 
                tl_fig.update_xaxes(title="", visible=False)
                tl_fig.update_layout(
                    showlegend=False, height=220, 
                    margin=dict(l=0, r=0, t=10, b=0),
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(tl_fig, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info("No upcoming activities to display.")
        else:
            st.info("No activities defined.")

    with r3_col2:
        col_ms_h, col_ms_b = st.columns([3, 1])
        with col_ms_h: st.markdown("### Major Milestones")
        
        if not all_activities.empty:
            milestones = all_activities.sort_values('planned_start')
            with col_ms_b:
                st.markdown('<div class="list-btn">', unsafe_allow_html=True)
                if st.button("All Stages", key="btn_full_ms", use_container_width=True): show_full_milestones(milestones)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # UPDATED: Show responsible person and output download
            ms_html = '<div style="background-color: var(--card-bg); padding: 15px; border-radius: 12px; border: 1px solid rgba(128, 128, 128, 0.1); box-shadow: 0 2px 5px rgba(0,0,0,0.02); min-height: 220px;">'
            for _, row in milestones.head(4).iterrows():
                status_label = row['status_mapped']
                status_color = COLORS['status_complete'] if status_label == 'Complete' else (COLORS['status_active'] if status_label == 'Active' else COLORS['status_not_started'])
                icon = "Done" if status_label == 'Complete' else ("Active" if status_label == 'Active' else "Pending")
                
                responsible_badge = ""
                if pd.notna(row.get('responsible_name')) and row['responsible_name']:
                    responsible_badge = f'<span class="badge-sm" style="background:rgba(95, 162, 232, 0.1); color:#5fa2e8; border:1px solid rgba(128, 128, 128, 0.2);">{row["responsible_name"]}</span>'
                
                ms_html += f'<div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(128, 128, 128, 0.1); padding:12px 0;"><div><span style="font-weight:500; font-size:0.9rem; display:block;">{row["activity_name"]}</span>{responsible_badge}</div><div style="text-align:right;"><span style="display:block; font-size:0.75rem; opacity:0.8;">{row["planned_finish"]}</span><span style="display:block; font-size:0.8rem; color:{status_color}; font-weight:600;">{icon} {status_label}</span></div></div>'
            ms_html += '</div>'
            st.markdown(ms_html, unsafe_allow_html=True)
        else:
            st.info("No milestones defined.")

    st.markdown('<div style="height:30px"></div>', unsafe_allow_html=True)

    # --- ROW 4: BUDGET BURNDOWN ---
    st.markdown("### Budget Burndown")
    bd = calculations.get_burndown_data(project_id)
    if bd:
        status_styles = {
            "On Track":   (COLORS['status_active'],   "OK"),
            "At Risk":    (COLORS['status_not_started'], "Risk"),
            "Over Budget":(COLORS['status_critical'], "Over"),
            "No Data":    (COLORS['subtext'],          "Info"),
        }
        bd_status = bd["status"]
        stat_color, stat_icon = status_styles.get(bd_status, (COLORS['subtext'], "Info"))

        burn_col1, burn_col2, burn_col3 = st.columns([1, 1, 1])
        with burn_col1:
            st.markdown(f'<div class="kpi-card"><div class="kpi-value" style="font-size:1.3rem;">R {bd["total_budget"]:,.0f}</div><div class="kpi-label">Total Budget</div></div>', unsafe_allow_html=True)
        with burn_col2:
            days_rem = max((bd["end_date"] - bd["today"]).days, 0) if bd["end_date"] else 0
            st.markdown(f'<div class="kpi-card" style="border-left-color:{COLORS["fin_forecast"]}"><div class="kpi-value" style="font-size:1.3rem; color:{COLORS["fin_forecast"]} !important;">{days_rem}</div><div class="kpi-label">Days Remaining</div></div>', unsafe_allow_html=True)
        with burn_col3:
            st.markdown(f'<div class="kpi-card" style="border-left-color:{stat_color}"><div class="kpi-value" style="font-size:1.1rem; color:{stat_color} !important;">{stat_icon} {bd_status}</div><div class="kpi-label">Budget Status</div></div>', unsafe_allow_html=True)

        st.markdown('<div style="height:15px"></div>', unsafe_allow_html=True)

        bd_fig = go.Figure()
        if not bd["ideal_df"].empty:
            bd_fig.add_trace(go.Scatter(x=bd["ideal_df"]["date"], y=bd["ideal_df"]["remaining"], mode="lines", name="Ideal Burndown", line=dict(color="#94a3b8", width=2, dash="dash"), hovertemplate="<b>Ideal</b><br>%{x|%d %b %Y}<br>Remaining: R %{y:,.0f}<extra></extra>"))
        if not bd["actual_df"].empty:
            bd_fig.add_trace(go.Scatter(x=bd["actual_df"]["date"], y=bd["actual_df"]["remaining"], mode="lines+markers", name="Actual Remaining", line=dict(color=COLORS['fin_actual'], width=3), marker=dict(size=6, color=COLORS['fin_actual']), hovertemplate="<b>Actual</b><br>%{x|%d %b %Y}<br>Remaining: R %{y:,.0f}<extra></extra>", fill="tozeroy", fillcolor="rgba(8, 145, 178, 0.08)"))
        if not bd["forecast_df"].empty:
            bd_fig.add_trace(go.Scatter(x=bd["forecast_df"]["date"], y=bd["forecast_df"]["remaining"], mode="lines", name="Forecast", line=dict(color=COLORS['status_critical'], width=2, dash="dot"), hovertemplate="<b>Forecast</b><br>%{x|%d %b %Y}<br>Remaining: R %{y:,.0f}<extra></extra>"))

        today_ts = bd["today"]
        bd_fig.add_vline(x=today_ts.timestamp() * 1000, line_width=1.5, line_dash="dot", line_color=COLORS['fin_forecast'], annotation_text="Today", annotation_position="top right", annotation_font=dict(color=COLORS['fin_forecast'], size=11))
        bd_fig.add_hline(y=0, line_width=1, line_dash="solid", line_color=COLORS['status_critical'], opacity=0.4)

        bd_fig.update_layout(
            height=340, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=12)),
            xaxis=dict(title="", showgrid=True, gridcolor="#f0f0f0", tickformat="%b %Y", tickfont=dict(size=11, color=COLORS['subtext'])),
            yaxis=dict(title="Remaining Budget (R)", showgrid=True, gridcolor="#f0f0f0", tickformat=",.0f", tickprefix="R ", tickfont=dict(size=11, color=COLORS['subtext']), rangemode="tozero"),
            hovermode="x unified"
        )
        st.plotly_chart(bd_fig, use_container_width=True, config={"displayModeBar": False})
        if bd["actual_df"].empty:
            st.info("No expenditure recorded yet — showing the ideal burndown baseline only.")
    else:
        st.warning("Could not load project dates or budget to render the burndown chart.")

    st.markdown('<div style="height:30px"></div>', unsafe_allow_html=True)

    # --- ROW 5: TASK DELIVERABLES (NEW) ---
    st.markdown("### <i class='fas fa-paperclip fa-icon'></i> Task Deliverables", unsafe_allow_html=True)
    
    all_outputs = database.get_all_outputs_for_project(project_id)
    
    if not all_outputs.empty:
        deliverables_html = '<div style="background-color: var(--card-bg); padding: 15px; border-radius: 12px; border: 1px solid rgba(128, 128, 128, 0.1); box-shadow: 0 2px 5px rgba(0,0,0,0.02);">'
        deliverables_html += '<div style="display:flex; padding:8px 0; border-bottom:2px solid rgba(128, 128, 128, 0.2); margin-bottom:4px;"><span style="flex:2; font-size:0.75rem; opacity:0.8; font-weight:600; text-transform:uppercase;">Task</span><span style="flex:2; font-size:0.75rem; opacity:0.8; font-weight:600; text-transform:uppercase;">Output File</span><span style="flex:1; font-size:0.75rem; opacity:0.8; font-weight:600; text-transform:uppercase;">Uploaded By</span><span style="flex:1; font-size:0.75rem; opacity:0.8; font-weight:600; text-transform:uppercase;">Date</span></div>'
        
        for _, out in all_outputs.iterrows():
            uploaded_date = str(out['uploaded_at'])[:10] if pd.notna(out['uploaded_at']) else 'N/A'
            deliverables_html += f'<div class="deliverable-row"><span style="flex:2; font-weight:500; font-size:0.9rem;">{out["activity_name"]}</span><span style="flex:2; font-size:0.85rem; color:#5fa2e8;">{out["file_name"]}</span><span style="flex:1; font-size:0.8rem; opacity:0.8;">{out["uploader_name"]}</span><span style="flex:1; font-size:0.8rem; opacity:0.8;">{uploaded_date}</span></div>'
        
        deliverables_html += '</div>'
        st.markdown(deliverables_html, unsafe_allow_html=True)
        
        # Download buttons
        st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
        dl_cols = st.columns(min(len(all_outputs), 4))
        for i, (_, out) in enumerate(all_outputs.iterrows()):
            file_full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', out['file_path'])
            if os.path.exists(file_full_path):
                with dl_cols[i % len(dl_cols)]:
                    st.markdown('<div class="download-btn">', unsafe_allow_html=True)
                    with open(file_full_path, "rb") as fp:
                        st.download_button(
                            out['file_name'], data=fp.read(),
                            file_name=out['file_name'], key=f"dash_dl_{out['output_id']}",
                            use_container_width=True
                        )
                    st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No deliverables uploaded yet. Outputs will appear here once tasks are marked as complete with uploaded files.")

    st.markdown('<div style="height:30px"></div>', unsafe_allow_html=True)

    # --- ROW 6: RISK REGISTER ---
    st.markdown("### Risk Register")
    risks = database.get_project_risks(project_id)
    
    if not risks.empty:
        r4_col1, r4_col2 = st.columns([2, 1])
        
        with r4_col1:
            risk_html = '<div style="background-color: var(--card-bg); padding: 15px; border-radius: 12px; border: 1px solid rgba(128, 128, 128, 0.1); box-shadow: 0 2px 5px rgba(0,0,0,0.02);">'
            for _, row in risks.iterrows():
                impact_code = row['impact']
                impact_color = COLORS['risk_high'] if impact_code == 'H' else (COLORS['risk_medium'] if impact_code == 'M' else COLORS['risk_low'])
                status_icon = "High" if impact_code == 'H' else ("Med" if impact_code == 'M' else "Low")
                risk_html += f"""
<div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(128, 128, 128, 0.1); padding:12px 0;">
    <div style="flex:1; padding-right:10px;">
        <span style="font-weight:500; font-size:0.9rem; display:block;">{row["description"]}</span>
        <span style="font-size:0.75rem; opacity:0.8;">Plan: {row['mitigation_action'] or 'None'}</span>
    </div>
    <div style="text-align:right; min-width:80px;">
        <span style="display:block; font-size:0.75rem; opacity:0.8;">{row["date_identified"]}</span>
        <span style="display:block; font-size:0.8rem; color:{impact_color}; font-weight:600;">{status_icon} {impact_code}-Impact</span>
    </div>
</div>
"""
            risk_html += '</div>'
            st.markdown(risk_html, unsafe_allow_html=True)
            
        with r4_col2:
            high_risks = len(risks[risks['impact'] == 'H'])
            open_risks = len(risks[risks['status'] == 'Open'])
            mc1, mc2 = st.columns(2)
            with mc1:
                st.markdown(f"""
<div class="kpi-card" style="border-left-color: {COLORS['risk_medium'] if open_risks > 0 else COLORS['risk_low']}; padding: 10px;">
    <div class="kpi-value" style="font-size: 1.4rem; color: {COLORS['risk_medium'] if open_risks > 0 else COLORS['risk_low']} !important;">{open_risks}</div>
    <div class="kpi-label" style="font-size: 0.7rem;">Active</div>
</div>
""", unsafe_allow_html=True)
            with mc2:
                crit_color = COLORS['risk_high'] if high_risks > 0 else COLORS['risk_low']
                st.markdown(f"""
<div class="kpi-card" style="border-left-color: {crit_color}; padding: 10px;">
    <div class="kpi-value" style="font-size: 1.4rem; color: {crit_color} !important;">{high_risks}</div>
    <div class="kpi-label" style="font-size: 0.7rem;">Critical</div>
</div>
""", unsafe_allow_html=True)
            
            st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
            
            if not risks.empty:
                total_risks = len(risks)
                high_pct = (len(risks[risks['impact'] == 'H']) / total_risks) * 100
                med_pct = (len(risks[risks['impact'] == 'M']) / total_risks) * 100
                low_pct = (len(risks[risks['impact'] == 'L']) / total_risks) * 100
                st.markdown(f"""
                <div style="margin-top: 5px;">
                    <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 5px; font-weight: 600; text-transform: uppercase;">Risk Distribution</div>
                    <div style="display: flex; height: 8px; width: 100%; background-color: #f1f5f9; border-radius: 4px; overflow: hidden;">
                        <div style="width: {high_pct}%; background-color: {COLORS['risk_high']};"></div>
                        <div style="width: {med_pct}%; background-color: {COLORS['risk_medium']};"></div>
                        <div style="width: {low_pct}%; background-color: {COLORS['risk_low']};"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-top: 4px; font-size: 0.7rem; color: #94a3b8;">
                        <span>High ({int(high_pct)}%)</span>
                        <span>Medium ({int(med_pct)}%)</span>
                        <span>Low ({int(low_pct)}%)</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("✅ No risks or issues identified for this project.")

if __name__ == "__main__":
    pm_dashboard()
