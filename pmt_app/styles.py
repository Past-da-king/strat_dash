import streamlit as st


def global_css():
    """Inject theme-aware premium global CSS into the Streamlit application."""
    # Inject external assets via HTML link tags for better reliability
    st.markdown(
        """
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
    <style>

        /* --- Sidebar Hiding Logic --- */
        #root:has(.hide-sidebar) [data-testid="stSidebar"] {{
            display: none !important;
        }}

        .stApp:has(.hide-sidebar) [data-testid="stSidebarNav"] {{
            display: none !important;
        }}

        /* --- Icon & Utility Classes --- */
        .fa-icon {{
            margin-right: 8px;
            color: var(--primary-light);
        }}

        /* --- Root Variables (Theme-Aware) --- */
        :root {{
            --primary-color: #0c4a6e;
            --primary-light: #0ea5e9;
            --primary-gradient: linear-gradient(135deg, #0c4a6e 0%, #0ea5e9 100%);
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --danger-color: #ef4444;
            
            /* Use inherit or Streamlit variables for text to support light/dark modes */
            --radius-sm: 8px;
            --radius-md: 12px;
            --radius-lg: 16px;
            --shadow-sm: 0 2px 4px rgba(0,0,0,0.05);
            --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
            --shadow-lg: 0 8px 24px rgba(0,0,0,0.12);
        }}

        /* --- Page-Level Animation --- */
        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(12px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .stMainBlockContainer {{
            animation: fadeInUp 0.4s ease-out;
        }}

        /* --- Global Typography --- */
        .stMarkdown:not(.badge), .stTextInput label, .stSelectbox label, 
        .stNumberInput label, .stDateInput label, .stMultiSelect label {{
            font-family: 'Inter', sans-serif !important;
            color: #ffffff !important; 
        }}

        h1, h2, h3, h4, h5, h6 {{
            font-family: 'Inter', sans-serif !important;
            letter-spacing: -0.5px !important;
            color: #5fa2e8 !important; /* Force a readable light blue for headers */
        }}

        /* --- Button Styling --- */
        /* NUCLEAR RESET: Force buttons inside popovers to be text-only */
        [data-testid="stPopoverContent"] button,
        [data-testid="stPopoverContent"] [data-testid^="baseButton"],
        [data-testid="stPopoverContent"] div,
        [data-testid="stPopoverContent"] a,
        [data-testid="stPopoverContent"] summary {{
            background: transparent !important;
            background-color: transparent !important;
            background-image: none !important;
            border: none !important;
            box-shadow: none !important;
            outline: none !important;
            border-radius: 0 !important;
            min-height: unset !important;
            height: auto !important;
            width: auto !important;
            padding: 4px 0 !important;
            color: #38bdf8 !important;
            text-align: left !important;
            justify-content: flex-start !important;
            text-decoration: none !important;
        }}

        [data-testid="stPopoverContent"] button p,
        [data-testid="stPopoverContent"] button div {{
            margin: 0 !important;
            padding: 0 !important;
            color: inherit !important;
            font-size: 0.95rem !important;
            font-weight: 500 !important;
        }}

        /* Hover Feedback */
        [data-testid="stPopoverContent"] button:hover,
        [data-testid="stPopoverContent"] button:hover p,
        [data-testid="stPopoverContent"] a:hover {{
            text-decoration: underline !important;
            color: #7dd3fc !important;
            background: transparent !important;
        }}

        /* Red Delete Link Specificity */
        [data-testid="stPopoverContent"] button:has(p:contains("Delete")),
        [data-testid="stPopoverContent"] button:has(div:contains("Delete")),
        [data-testid="stPopoverContent"] button:has(p:contains("Permanent")) {{
            color: #f87171 !important;
        }}
        [data-testid="stPopoverContent"] button:has(p:contains("Delete")) p,
        [data-testid="stPopoverContent"] button:has(p:contains("Permanent")) p {{
            color: #f87171 !important;
        }}

        /* Wipe out expander box look inside popovers */
        [data-testid="stPopoverContent"] [data-testid="stExpander"] {{
            border: none !important;
            background: transparent !important;
            margin: 0 !important;
        }}
        [data-testid="stPopoverContent"] [data-testid="stExpander"] summary svg {{
            display: none !important;
        }}

        /* Global Buttons (Outside Popovers only) */
        button[data-testid="baseButton-secondary"]:not([data-testid="stPopoverContent"] *), 
        button[data-testid="baseButton-primary"]:not([data-testid="stPopoverContent"] *),
        .stButton > button:not([data-testid="stPopoverContent"] *), 
        .stDownloadButton > button:not([data-testid="stPopoverContent"] *) {{
            color: white !important;
            background: var(--primary-gradient) !important;
            border: none !important;
            border-radius: var(--radius-sm) !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
        }}

        /* Download Button Specific (Outside Popovers) */
        .stDownloadButton > button:not([data-testid="stPopoverContent"] *) {{
            background: linear-gradient(135deg, #059669 0%, #34d399 100%) !important;
        }}

        /* --- Metric & KPI Card Styling (Theme-Aware) --- */
        [data-testid="stMetric"], .kpi-card {{
            background-color: rgba(255, 255, 255, 0.05) !important; /* Subtle background for both modes */
            border: 1px solid rgba(128, 128, 128, 0.2) !important;
            border-radius: var(--radius-md) !important;
            padding: 1rem 1.2rem !important;
            box-shadow: var(--shadow-sm) !important;
            transition: all 0.3s ease !important;
        }}

        [data-testid="stMetricValue"], .kpi-value {{
            font-weight: 700 !important;
            color: var(--primary-light) !important; /* Lighter blue for better visibility on dark */
        }}

        [data-testid="stMetricLabel"], .kpi-label {{
            font-weight: 500 !important;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            font-size: 0.75rem !important;
            opacity: 0.8;
        }}

        .kpi-card {{
            border-left: 5px solid var(--primary-color) !important;
            text-align: center;
        }}

        /* --- Health Icons --- */
        .health-icon {{
            width: 42px; height: 42px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.1rem; font-weight: 700;
        }}

/* --- Sidebar --- */
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%) !important;
        }}

        .brand-logo-img {{
            width: 44px;
            height: auto;
            flex-shrink: 0;
        }}

        .brand-text-block {{
            display: flex;
            flex-direction: column;
            line-height: 1;
        }}

        .brand-title-main {{
            color: white;
            font-size: 1.15rem;
            font-weight: 800;
            letter-spacing: -0.5px;
            font-family: 'Inter', sans-serif;
        }}

        .brand-subtitle-main {{
            color: #38bdf8;
            font-size: 0.58rem;
            font-weight: 700;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            font-family: 'Inter', sans-serif;
            margin-top: 2px;
        }}

        .stTabs [aria-selected="true"] {{
            color: var(--primary-light) !important;
            border-bottom: 3px solid var(--primary-light) !important;
        }}

        /* --- Tab Icon Injection (FontAwesome via CSS) --- */
        [data-testid="stTitleBlock"] + div .stTabs [data-baseweb="tab"]:nth-child(1) div:before {{
            content: "\\f084"; font-family: "Font Awesome 6 Free"; font-weight: 900; margin-right: 8px;
        }}
        [data-testid="stTitleBlock"] + div .stTabs [data-baseweb="tab"]:nth-child(2) div:before {{
            content: "\\f234"; font-family: "Font Awesome 6 Free"; font-weight: 900; margin-right: 8px;
        }}

        /* --- Action Button Icons (FontAwesome via CSS) --- */
        /* Targeting multiple possible Streamlit button DOM structures */
        .exec-btn button [data-testid="stMarkdownContainer"] p:before {{ content: "\\f201"; font-family: "Font Awesome 6 Free"; font-weight: 900; margin-right: 8px; }}
        .pm-btn button [data-testid="stMarkdownContainer"] p:before {{ content: "\\f0ae"; font-family: "Font Awesome 6 Free"; font-weight: 900; margin-right: 8px; }}
        .logout-btn button [data-testid="stMarkdownContainer"] p:before {{ content: "\\f2f5"; font-family: "Font Awesome 6 Free"; font-weight: 900; margin-right: 8px; }}
        .add-btn button [data-testid="stMarkdownContainer"] p:before {{ content: "\\f0fe"; font-family: "Font Awesome 6 Free"; font-weight: 900; margin-right: 8px; }}
        .save-btn button [data-testid="stMarkdownContainer"] p:before {{ content: "\\f0c7"; font-family: "Font Awesome 6 Free"; font-weight: 900; margin-right: 8px; }}
        .delete-btn button [data-testid="stMarkdownContainer"] p:before {{ content: "\\f2ed"; font-family: "Font Awesome 6 Free"; font-weight: 900; margin-right: 8px; }}
        .refresh-btn button [data-testid="stMarkdownContainer"] p:before {{ content: "\\f2f1"; font-family: "Font Awesome 6 Free"; font-weight: 900; margin-right: 8px; }}
        .download-btn button [data-testid="stMarkdownContainer"] p:before {{ content: "\\f0ab"; font-family: "Font Awesome 6 Free"; font-weight: 900; margin-right: 8px; }}
        .report-btn button [data-testid="stMarkdownContainer"] p:before {{ content: "\\f1c1"; font-family: "Font Awesome 6 Free"; font-weight: 900; margin-right: 8px; }}
        .back-btn button [data-testid="stMarkdownContainer"] p:before {{ content: "\\f060"; font-family: "Font Awesome 6 Free"; font-weight: 900; margin-right: 8px; }}
        .info-btn button [data-testid="stMarkdownContainer"] p:before {{ content: "\\f05a"; font-family: "Font Awesome 6 Free"; font-weight: 900; margin-right: 8px; }}
        .upload-btn button [data-testid="stMarkdownContainer"] p:before {{ content: "\\f093"; font-family: "Font Awesome 6 Free"; font-weight: 900; margin-right: 8px; }}
        .check-btn button [data-testid="stMarkdownContainer"] p:before {{ content: "\\f00c"; font-family: "Font Awesome 6 Free"; font-weight: 900; margin-right: 8px; }}
        .chart-btn button [data-testid="stMarkdownContainer"] p:before {{ content: "\\f080"; font-family: "Font Awesome 6 Free"; font-weight: 900; margin-right: 8px; }}
        .list-btn button [data-testid="stMarkdownContainer"] p:before {{ content: "\\f03a"; font-family: "Font Awesome 6 Free"; font-weight: 900; margin-right: 8px; }}
        .settings-btn button [data-testid="stMarkdownContainer"] p:before {{ content: "\\f013"; font-family: "Font Awesome 6 Free"; font-weight: 900; margin-right: 8px; }}
        .project-btn button [data-testid="stMarkdownContainer"] p:before {{ content: "\\f5fd"; font-family: "Font Awesome 6 Free"; font-weight: 900; margin-right: 8px; }}
        
        /* Fallback for different DOM versions */
        [class*="-btn"] button div:before {{ font-family: "Font Awesome 6 Free"; font-weight: 900; }}

        /* --- Forms & Inputs --- */
        .stTextInput > div > div > input,
        .stSelectbox > div > div,
        .stNumberInput > div > div > input,
        .stDateInput > div > div > input {{
            border-radius: var(--radius-sm) !important;
        }}

        /* --- Table/Dataframe --- */
        [data-testid="stDataFrame"] {{
            border: 1px solid rgba(128, 128, 128, 0.1) !important;
        }}

        /* --- Completed Task Card Accent --- */
        .task-card-complete {{
            border-left: 5px solid var(--success-color) !important;
            background: rgba(76, 175, 80, 0.05) !important;
        }}

        .task-card {{
            background: rgba(128, 128, 128, 0.05) !important;
            border: 1px solid rgba(128, 128, 128, 0.1) !important;
            border-radius: var(--radius-md);
            padding: 1.2rem;
            margin-bottom: 0.8rem;
        }}

        /* --- Executive Dashboard Project Cards --- */
        .project-card {{
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(128, 128, 128, 0.1) !important;
            border-radius: var(--radius-lg) !important;
            padding: 1.5rem !important;
            margin-bottom: 1rem !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: var(--shadow-md) !important;
        }}
        .project-card:hover {{
            transform: translateY(-5px) !important;
            box-shadow: var(--shadow-lg) !important;
            border-color: var(--primary-light) !important;
            background: rgba(255, 255, 255, 0.05) !important;
        }}
        .project-card-title {{
            font-size: 1.25rem !important;
            font-weight: 700 !important;
            color: #ffffff !important;
            margin-bottom: 0.25rem !important;
        }}
        .project-card-meta {{
            font-size: 0.85rem !important;
            color: rgba(255, 255, 255, 0.6) !important;
            margin-bottom: 1.25rem !important;
        }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        .metric-box {{
            background: rgba(0, 0, 0, 0.2) !important;
            padding: 0.8rem !important;
            border-radius: var(--radius-md) !important;
            text-align: center !important;
            border: 1px solid rgba(128, 128, 128, 0.05) !important;
        }}
        .metric-box-label {{
            font-size: 0.7rem !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            color: rgba(255, 255, 255, 0.5) !important;
            margin-bottom: 0.3rem !important;
        }}
        .metric-box-value {{
            font-size: 1.1rem !important;
            font-weight: 700 !important;
            color: var(--primary-light) !important;
        }}
        .progress-container {{
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            height: 10px;
            overflow: hidden;
            margin-bottom: 1.5rem;
            position: relative;
        }}
        .progress-fill {{
            height: 100%;
            background: var(--primary-gradient);
            border-radius: 10px;
            transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        
        /* --- Operational Task Cards (Record Activity) --- */
        [data-testid="stVerticalBlockBorderWrapper"] {{
            background: rgba(255, 255, 255, 0.02) !important;
            border: 1px solid rgba(128, 128, 128, 0.1) !important;
            border-radius: var(--radius-md) !important;
            transition: border-color 0.3s ease !important;
            padding: 0 !important;
        }}
        [data-testid="stVerticalBlockBorderWrapper"]:hover {{
            border-color: rgba(95, 162, 232, 0.4) !important;
        }}
        .op-title {{
            font-size: 1.1rem !important;
            font-weight: 600 !important;
            color: #ffffff !important;
            margin-bottom: 0.2rem !important;
        }}
        .op-meta {{
            font-size: 0.8rem !important;
            color: rgba(255, 255, 255, 0.5) !important;
            margin-bottom: 0.75rem !important;
        }}
        
        /* --- Download Badge --- */
        .download-btn-subtle button {{
            background: rgba(16, 185, 129, 0.1) !important;
            color: #10b981 !important;
            border: 1px solid rgba(16, 185, 129, 0.2) !important;
            font-size: 0.8rem !important;
            padding: 0.4rem 0.8rem !important;
            height: auto !important;
        }}
        .download-btn-subtle button:hover {{
            background: rgba(16, 185, 129, 0.2) !important;
            border-color: #10b981 !important;
        }}

        /* --- Summary Metric Cards (Record Activity) --- */
        .stat-card {{
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(128, 128, 128, 0.1) !important;
            border-radius: var(--radius-md) !important;
            padding: 1rem !important;
            text-align: left !important;
        }}
        .stat-label {{
            font-size: 0.7rem !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            color: rgba(255, 255, 255, 0.5) !important;
            margin-bottom: 0.5rem !important;
        }}
        .stat-value-container {{
            display: flex !important;
            align-items: baseline !important;
            gap: 10px !important;
        }}
        .stat-value {{
            font-size: 1.8rem !important;
            font-weight: 700 !important;
            color: var(--primary-light) !important;
            line-height: 1 !important;
        }}
        .stat-delta {{
            font-size: 0.85rem !important;
            font-weight: 600 !important;
            padding: 2px 8px !important;
            border-radius: 4px !important;
            background: rgba(16, 185, 129, 0.1) !important;
            color: #10b981 !important;
        }}

        /* --- Scrollbar --- */
        ::-webkit-scrollbar-thumb {{
            background: rgba(128, 128, 128, 0.3);
            border-radius: 3px;
        }}

    </style>
    """,
        unsafe_allow_html=True,
    )
