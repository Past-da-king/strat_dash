import streamlit as st
import database
import auth
import styles
import os
from pathlib import Path

# Portable logo path — image lives in pmt_app/image/image.png
LOGO_PATH = Path(__file__).parent / "image" / "image.png"
# Read as bytes for reliable rendering on any platform or host
with open(LOGO_PATH, "rb") as _f:
    LOGO_BYTES = _f.read()

# Page Config (Set this first)
st.set_page_config(
    page_title="Strat Edge Project Portal",
    page_icon=LOGO_BYTES,
    layout="wide",
    initial_sidebar_state="expanded"
)

def home_view():
    """The default home view after login."""
    styles.global_css()
    user = auth.get_current_user()
    
    st.markdown(f"""
    <div style="background: rgba(255, 255, 255, 0.05); padding: 2.5rem; border-radius: 16px; border: 1px solid rgba(128, 128, 128, 0.2); box-shadow: 0 4px 20px rgba(0,0,0,0.1); text-align: center; margin-top: 2rem;">
        <div style="font-size: 1.5rem; opacity: 0.8; margin-bottom: 0.5rem;">Hello,</div>
        <div style="font-size: 2.5rem; font-weight: 700; color: #0ea5e9; margin-bottom: 1rem;">{user['full_name']}</div>
        <div style="display: inline-block; padding: 4px 12px; background: rgba(14, 165, 233, 0.1); color: #0ea5e9; border-radius: 20px; font-weight: 600; font-size: 0.85rem; margin-bottom: 2rem;">
            {user['role'].upper()} ACCESS
        </div>
        <div style="opacity: 0.8; margin-bottom: 1.5rem;">
            Welcome to the Strat Edge Project Performance Portal.
        </div>
        <div style="background: rgba(12, 74, 110, 0.2); padding: 1.5rem; border-radius: 12px; margin-top: 1rem; border: 1px dashed rgba(14, 165, 233, 0.4);">
            <div style="font-weight: 700; color: #38bdf8; font-size: 0.95rem; margin-bottom: 4px;">STRAT EDGE SOLUTIONS</div>
            <div style="font-size: 0.8rem; font-style: italic; opacity: 0.9;">"Turning Insight into Advantage"</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="exec-btn">', unsafe_allow_html=True)
        if st.button("Executive Overview", use_container_width=True):
            st.switch_page("views/1_Executive_Dashboard.py")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="pm-btn">', unsafe_allow_html=True)
        if st.button("Project Management", use_container_width=True):
            st.switch_page("views/2_PM_Dashboard.py")
        st.markdown('</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        if st.button("Logout", type="primary", use_container_width=True):
            auth.logout()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

def login_view():
    """The view for non-logged in users."""
    styles.global_css()
    st.markdown('<div class="hide-sidebar"></div>', unsafe_allow_html=True)

    # Vertically center everything with top padding
    st.markdown('<div style="height: 6vh;"></div>', unsafe_allow_html=True)

    col_space1, col_form, col_space2 = st.columns([1.5, 2, 1.5])

    with col_form:
        # --- COMPACT HEADER: small logo + company name side by side ---
        h_left, h_logo, h_text, h_right = st.columns([1, 1, 3, 1])
        with h_logo:
            st.image(LOGO_BYTES, width=55)
        with h_text:
            st.markdown("""
                <div style="display: flex; flex-direction: column; justify-content: center; height: 100%; padding-top: 8px;">
                    <div style="color: white; font-size: 1.3rem; font-weight: 800; letter-spacing: -0.5px; line-height: 1.1;">STRAT EDGE</div>
                    <div style="color: #38bdf8; font-size: 0.65rem; font-weight: 600; letter-spacing: 3px; margin-top: 3px;">PROJECT PORTAL</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("""
            <div style="text-align: center; color: #64748b; font-size: 0.72rem; font-style: italic; margin-top: 4px; margin-bottom: 18px; opacity: 0.85;">
                "Turning Insight into Advantage"
            </div>
        """, unsafe_allow_html=True)

        # Tabs for Login/Signup
        tab_login, tab_signup = st.tabs(["LOGIN", "REGISTER"])

        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                st.markdown('<div style="color: #38bdf8; font-size: 1.2rem; font-weight: 700; margin-bottom: 8px;">Welcome Back</div>', unsafe_allow_html=True)
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                st.markdown('<div class="exec-btn">', unsafe_allow_html=True)
                submit = st.form_submit_button("LOGIN", use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

                if submit:
                    if auth.login(username, password):
                        st.success("Login successful! Redirecting...")
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

        with tab_signup:
            with st.form("signup_form"):
                st.markdown("### Create Account")
                st.info("Your account will require administrator approval before you can log in.")
                new_user = st.text_input("Username *")
                new_pass = st.text_input("Password *", type="password")
                new_name = st.text_input("Full Name *")
                new_role = st.selectbox("Requested Role", ["pm", "executive", "team"])

                st.markdown('<div class="add-btn">', unsafe_allow_html=True)
                signup_submit = st.form_submit_button("REGISTER", use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

                if signup_submit:
                    if not new_user or not new_pass or not new_name:
                        st.error("All fields are required.")
                    elif database.get_user_by_username(new_user):
                        st.error("Username already exists.")
                    else:
                        from werkzeug.security import generate_password_hash
                        try:
                            database.create_user({
                                'username': new_user,
                                'password_hash': generate_password_hash(new_pass),
                                'full_name': new_name,
                                'role': new_role,
                                'status': 'pending'
                            })
                            st.success("Registration submitted! Please wait for admin approval.")
                        except Exception as e:
                            st.error(f"Error: {e}")

    st.markdown("""
        <div style="text-align: center; margin-top: 2rem; color: #334155; font-size: 0.72rem; letter-spacing: 1px;">
            © 2026 STRAT EDGE SOLUTIONS. ALL RIGHTS RESERVED.
        </div>
    """, unsafe_allow_html=True)


def main():
    # Initialize session state for auth
    auth.init_session()
    
    if not auth.is_logged_in():
        login_view()
    else:
        user = auth.get_current_user()
        role = user['role']
        
        # Define Pages
        home_page = st.Page(home_view, title="Dashboard Home", icon=":material/home:", default=True)
        
        exec_dash = st.Page("views/1_Executive_Dashboard.py", title="Executive Portfolio", icon=":material/dashboard:")
        pm_dash = st.Page("views/2_PM_Dashboard.py", title="Project Dashboard", icon=":material/analytics:")
        proj_setup = st.Page("views/3_Project_Setup.py", title="Project Setup", icon=":material/add_business:")
        record_act = st.Page("views/4_Record_Activity.py", title="Record Activity", icon=":material/bolt:")
        record_exp = st.Page("views/5_Record_Expenditure.py", title="Record Expenditure", icon=":material/payments:")
        risk_reg = st.Page("views/5_Risk_Register.py", title="Risk Register", icon=":material/warning:")
        admin_panel = st.Page("views/6_Admin_Panel.py", title="Admin Panel", icon=":material/admin_panel_settings:")
        admin_settings = st.Page("views/6_Admin_Settings.py", title="System Settings", icon=":material/settings:")
        logout = st.Page(auth.logout, title="Logout", icon=":material/logout:")

        # Role-based filtering
        pages = [home_page]
        
        if role in ['admin', 'executive']:
            pages.append(exec_dash)
            
        if role in ['pm', 'admin', 'executive']:
            pages.append(pm_dash)
            pages.append(proj_setup)
            
        # Everyone (team, pm, admin, executive) gets these
        pages.append(record_act)
        pages.append(record_exp)
        pages.append(risk_reg)
        
        if role in ['admin', 'executive']:
            pages.append(admin_panel)
            pages.append(admin_settings)
            
        pages.append(logout)
        
        # Initialize Navigation
        pg = st.navigation(pages)
        pg.run()

if __name__ == "__main__":
    main()
