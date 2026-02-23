import streamlit as st

def global_css():
    """Inject theme-aware premium global CSS into the Streamlit application."""
    st.markdown(f"""
    <style>
        /* ========================================
           GLOBAL DESIGN SYSTEM - PM TOOL v2.1
           ======================================== */

        /* --- Font Import --- */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css');

        /* --- Sidebar Hiding Logic --- */
        #root:has(.hide-sidebar) [data-testid="stSidebar"] {
            display: none !important;
        }

        .stApp:has(.hide-sidebar) [data-testid="stSidebarNav"] {
            display: none !important;
        }

        /* --- Icon & Utility Classes --- */
        .fa-icon {
            margin-right: 8px;
            color: var(--primary-light);
        }

        /* --- Root Variables (Theme-Aware) --- */
        :root {{
            --primary-color: #2c5aa0;
            --primary-light: #5fa2e8;
            --primary-gradient: linear-gradient(135deg, #2c5aa0 0%, #5fa2e8 100%);
            --success-color: #4caf50;
            --warning-color: #ffc107;
            --danger-color: #f44336;
            
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
        button[data-testid="baseButton-secondary"], 
        button[data-testid="baseButton-primary"],
        .stButton > button, 
        .stDownloadButton > button {{
            color: white !important;
            background: var(--primary-gradient) !important;
            border: none !important;
            border-radius: var(--radius-sm) !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
        }}

        /* Secondary/Ghost Buttons */
        .stButton > button[kind="secondary"] {{
            background: transparent !important;
            color: var(--primary-color) !important;
            border: 2px solid var(--primary-color) !important;
        }}

        /* --- Download Button --- */
        .stDownloadButton > button {{
            background: linear-gradient(135deg, #059669 0%, #34d399 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: var(--radius-sm) !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
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

        /* --- Sidebar & Tabs --- */
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%) !important;
        }}

        .stTabs [aria-selected="true"] {{
            color: var(--primary-light) !important;
            border-bottom: 3px solid var(--primary-light) !important;
        }}

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
    """, unsafe_allow_html=True)
