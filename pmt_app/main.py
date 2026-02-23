import streamlit as st
import database
import auth
import styles
import os

# Page Config
st.set_page_config(
    page_title="PM Tool - Login",
    page_icon="🔒",
    layout="centered",
    initial_sidebar_state="collapsed"
)

def main():
    # Initialize session state for auth
    auth.init_session()
    
    # Apply Global Styles
    styles.global_css()

    # --- BRANDING ---
    st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem; margin-top: 3rem;">
            <div style="background: linear-gradient(135deg, #2c5aa0 0%, #5fa2e8 100%); 
                        -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
                        font-size: 3.5rem; font-weight: 800; letter-spacing: -2px;">
                PM PORTAL
            </div>
            <p style="color: grey; font-size: 1.1rem; font-weight: 500; opacity: 0.9;">
                Enterprise Project Performance Dashboard
            </p>
        </div>
    """, unsafe_allow_html=True)

    if not auth.is_logged_in():
        # Tabs for Login/Signup
        tab_login, tab_signup = st.tabs(["🔑 LOGIN", "📝 REGISTER"])
        
        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                st.markdown("### Welcome Back")
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("LOGIN")
                
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
                new_role = st.selectbox("Requested Role", ["pm", "executive", "recorder"])
                
                signup_submit = st.form_submit_button("REGISTER")
                
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
            <div style="text-align: center; margin-top: 3rem; color: #94a3b8; font-size: 0.8rem;">
                © 2026 PM Tool Enterprise. All rights reserved.
            </div>
        """, unsafe_allow_html=True)

    else:
        # LOGGED IN VIEW - Welcome & Navigation Quick Links
        user = auth.get_current_user()
        
        st.markdown(f"""
        <div style="background: rgba(255, 255, 255, 0.05); padding: 2.5rem; border-radius: 16px; border: 1px solid rgba(128, 128, 128, 0.2); box-shadow: 0 4px 20px rgba(0,0,0,0.1); text-align: center;">
            <div style="font-size: 1.5rem; opacity: 0.8; margin-bottom: 0.5rem;">Hello,</div>
            <div style="font-size: 2.5rem; font-weight: 700; color: #5fa2e8; margin-bottom: 1rem;">{user['full_name']}</div>
            <div style="display: inline-block; padding: 4px 12px; background: rgba(95, 162, 232, 0.1); color: #5fa2e8; border-radius: 20px; font-weight: 600; font-size: 0.85rem; margin-bottom: 2rem;">
                {user['role'].upper()} ACCESS
            </div>
            <div style="opacity: 0.8; margin-bottom: 1rem;">
                Use the sidebar to navigate through your projects and dashboards.
            </div>
            <div style="background: rgba(44, 90, 160, 0.1); padding: 1rem; border-radius: 8px; margin-top: 1rem; border: 1px dashed rgba(95, 162, 232, 0.4);">
                <div style="font-weight: 600; color: #5fa2e8; font-size: 0.9rem;">📂 New Template Available!</div>
                <div style="font-size: 0.8rem; opacity: 0.9;">I've updated the Project Template with the new columns: <br><b>Responsible (Username)</b> and <b>Expected Output</b>.</div>
                <div style="font-size: 0.75rem; margin-top: 5px; opacity: 0.7;">Location: <code>DASHBOARD/templates/Project_Template.xlsx</code></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("📊 Executive Overview", use_container_width=True):
                st.switch_page("pages/1_Executive_Dashboard.py")
        with c2:
            if st.button("🏠 Project Management", use_container_width=True):
                st.switch_page("pages/2_PM_Dashboard.py")
        with c3:
            if st.button("🚪 Logout", type="primary", use_container_width=True):
                auth.logout()
                st.rerun()

if __name__ == "__main__":
    main()
