import streamlit as st
import database
import auth
import styles
import os
import base64
from pathlib import Path


# Page Config (Set this first)
@st.cache_resource
def get_logo_data():
    LOGO_PATH = Path(__file__).parent / "image" / "image.png"
    with open(LOGO_PATH, "rb") as _f:
        bytes_data = _f.read()
    b64_data = base64.b64encode(bytes_data).decode()
    return bytes_data, b64_data


LOGO_BYTES, LOGO_B64 = get_logo_data()

st.set_page_config(
    page_title="Strat Edge Project Portal",
    page_icon=LOGO_BYTES,
    layout="wide",
    initial_sidebar_state="expanded",
)


def home_view():
    """The default home view after login."""
    styles.global_css()
    user = auth.get_current_user()
    role = user["role"]

    st.markdown(
        f"""
    <div style="display: flex; align-items: center; justify-content: center; gap: 12px; margin-bottom: 1rem;">
        <img src="data:image/png;base64,{LOGO_B64}" width="52" style="flex-shrink: 0;" />
        <div>
            <div style="color: white; font-size: 1.4rem; font-weight: 800; letter-spacing: -0.5px; line-height: 1.1;">STRAT EDGE</div>
            <div style="color: #38bdf8; font-size: 0.65rem; font-weight: 700; letter-spacing: 3px; margin-top: 2px;">PROJECT PORTAL</div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
    <div style="background: rgba(255, 255, 255, 0.05); padding: 2rem; border-radius: 16px; border: 1px solid rgba(128, 128, 128, 0.2); box-shadow: 0 4px 20px rgba(0,0,0,0.1); display: flex; align-items: center; justify-content: space-between; margin-top: 2rem; margin-bottom: 2rem; flex-wrap: wrap; gap: 1rem;">
        <div>
            <div style="font-size: 1.2rem; opacity: 0.8; margin-bottom: 0.2rem;">Welcome back,</div>
            <div style="font-size: 2.2rem; font-weight: 700; color: #0ea5e9; margin-bottom: 0.5rem; letter-spacing: -0.5px;">{user["full_name"]}</div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="padding: 4px 12px; background: rgba(14, 165, 233, 0.1); color: #0ea5e9; border-radius: 20px; font-weight: 600; font-size: 0.85rem;">
                    {user["role"].upper()} ACCESS
                </div>
            </div>
        </div>
        <div style="text-align: right; opacity: 0.8; max-width: 350px;">
            <i class="fas fa-chart-line fa-2x" style="color: #38bdf8; margin-bottom: 10px;"></i>
            <div style="font-size: 0.95rem; line-height: 1.5;">Select a module below to manage your projects, track performance, or configure the system.</div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)

    # Role-based quick navigation
    btns = []
    if role in ["admin", "executive"]:
        btns.append(
            ("Executive Portfolio", "views/1_Executive_Dashboard.py", "exec-btn")
        )
        btns.append(("Project Dashboard", "views/2_PM_Dashboard.py", "pm-btn"))
        btns.append(("Admin Panel", "views/6_Admin_Panel.py", "add-btn"))
    elif role == "pm":
        btns.append(("Project Dashboard", "views/2_PM_Dashboard.py", "pm-btn"))
        btns.append(("Project Setup", "views/3_Project_Setup.py", "add-btn"))
        btns.append(("Record Activity", "views/4_Record_Activity.py", "exec-btn"))
    else:  # team
        btns.append(("Project Dashboard", "views/2_PM_Dashboard.py", "pm-btn"))
        btns.append(("Record Activity", "views/4_Record_Activity.py", "exec-btn"))
        btns.append(("Risk Register", "views/5_Risk_Register.py", "pm-btn"))

    # Render buttons
    cols = st.columns(len(btns) + 1)
    for i, (label, page, css_class) in enumerate(btns):
        with cols[i]:
            st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
            if st.button(label, use_container_width=True, key=f"nav_{i}"):
                st.switch_page(page)
            st.markdown("</div>", unsafe_allow_html=True)

    with cols[-1]:
        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        if st.button(
            "Logout", type="primary", use_container_width=True, key="nav_logout"
        ):
            auth.logout()
        st.markdown("</div>", unsafe_allow_html=True)


def login_view():
    """The view for non-logged in users."""
    styles.global_css()
    st.markdown('<div class="hide-sidebar"></div>', unsafe_allow_html=True)

    # Vertically center everything with top padding
    st.markdown('<div style="height: 6vh;"></div>', unsafe_allow_html=True)

    col_space1, col_form, col_space2 = st.columns([1.5, 2, 1.5])

    with col_form:
        # --- COMPACT HEADER using base64 inline image ---
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; justify-content: center; gap: 12px; margin-bottom: 8px;">
                <img src="data:image/png;base64,{LOGO_B64}" width="52" style="flex-shrink: 0;" />
                <div>
                    <div style="color: white; font-size: 1.4rem; font-weight: 800; letter-spacing: -0.5px; line-height: 1.1;">STRAT EDGE</div>
                    <div style="color: #38bdf8; font-size: 0.65rem; font-weight: 700; letter-spacing: 3px; margin-top: 2px;">PROJECT PORTAL</div>
                </div>
            </div>
            <div style="text-align: center; color: #64748b; font-size: 0.72rem; font-style: italic; margin-bottom: 20px;">
                &ldquo;Turning Insight into Advantage&rdquo;
            </div>
        """,
            unsafe_allow_html=True,
        )

        # Tabs for Login/Signup
        tab_login, tab_signup = st.tabs(["LOGIN", "REGISTER"])

        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                st.markdown(
                    '<div style="color: #38bdf8; font-size: 1.2rem; font-weight: 700; margin-bottom: 8px;">Welcome Back</div>',
                    unsafe_allow_html=True,
                )
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                st.markdown('<div class="exec-btn">', unsafe_allow_html=True)
                submit = st.form_submit_button("LOGIN", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

                if submit:
                    if auth.login(username, password):
                        st.success("Login successful! Redirecting...")
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

        with tab_signup:
            with st.form("signup_form"):
                st.markdown("### Create Account")
                st.info(
                    "Your account will require administrator approval before you can log in."
                )
                new_user = st.text_input("Username *")
                new_pass = st.text_input("Password *", type="password")
                new_name = st.text_input("Full Name *")
                new_role = st.selectbox("Requested Role", ["pm", "executive", "team"])

                st.markdown('<div class="add-btn">', unsafe_allow_html=True)
                signup_submit = st.form_submit_button(
                    "REGISTER", use_container_width=True
                )
                st.markdown("</div>", unsafe_allow_html=True)

                if signup_submit:
                    if not new_user or not new_pass or not new_name:
                        st.error("All fields are required.")
                    elif database.get_user_by_username(new_user):
                        st.error("Username already exists.")
                    else:
                        from werkzeug.security import generate_password_hash

                        try:
                            database.create_user(
                                {
                                    "username": new_user,
                                    "password_hash": generate_password_hash(new_pass),
                                    "full_name": new_name,
                                    "role": new_role,
                                    "status": "pending",
                                }
                            )
                            st.success(
                                "Registration submitted! Please wait for admin approval."
                            )
                        except Exception as e:
                            st.error(f"Error: {e}")

    st.markdown(
        """
        <div style="text-align: center; margin-top: 2rem; color: #334155; font-size: 0.72rem; letter-spacing: 1px;">
            © 2026 STRAT EDGE SOLUTIONS. ALL RIGHTS RESERVED.
        </div>
    """,
        unsafe_allow_html=True,
    )


def main():
    auth.init_session()

    import streamlit.components.v1 as components
    if "_set_cookie" in st.session_state:
        token = st.session_state["_set_cookie"]
        components.html(f'<script>document.cookie = "auth_token={token}; max-age=604800; path=/; samesite=strict";</script>', height=0)
        del st.session_state["_set_cookie"]
    elif "_del_cookie" in st.session_state:
        components.html('<script>document.cookie = "auth_token=; max-age=0; path=/; samesite=strict";</script>', height=0)
        del st.session_state["_del_cookie"]

    if not auth.is_logged_in():
        login_view()
    else:
        user = auth.get_current_user()
        role = user["role"]

        with st.sidebar:
            if st.button("Logout", icon=":material/logout:", use_container_width=True):
                auth.logout()

        home_page = st.Page(
            home_view, title="Dashboard Home", icon=":material/home:", default=True
        )

        exec_dash = st.Page(
            "views/1_Executive_Dashboard.py",
            title="Executive Portfolio",
            icon=":material/dashboard:",
        )
        pm_dash = st.Page(
            "views/2_PM_Dashboard.py",
            title="Project Dashboard",
            icon=":material/analytics:",
        )
        proj_setup = st.Page(
            "views/3_Project_Setup.py",
            title="Project Setup",
            icon=":material/add_business:",
        )
        record_act = st.Page(
            "views/4_Record_Activity.py",
            title="Record Activity",
            icon=":material/bolt:",
        )
        record_exp = st.Page(
            "views/5_Record_Expenditure.py",
            title="Record Expenditure",
            icon=":material/payments:",
        )
        risk_reg = st.Page(
            "views/5_Risk_Register.py", title="Risk Register", icon=":material/warning:"
        )
        repo_page = st.Page(
            "views/7_Project_Repository.py",
            title="Project Repository",
            icon=":material/folder_special:",
        )
        admin_panel = st.Page(
            "views/6_Admin_Panel.py",
            title="Admin Panel",
            icon=":material/admin_panel_settings:",
        )
        admin_settings = st.Page(
            "views/6_Admin_Settings.py",
            title="System Settings",
            icon=":material/settings:",
        )

        pages = [home_page]

        if role in ["admin", "executive"]:
            pages.append(exec_dash)

        if role in ["pm", "admin", "executive", "team"]:
            pages.append(pm_dash)

        if role in ["pm", "admin", "executive"]:
            pages.append(proj_setup)

        pages.append(record_act)
        pages.append(record_exp)
        pages.append(risk_reg)
        pages.append(repo_page)

        if role in ["admin", "executive"]:
            pages.append(admin_panel)
            pages.append(admin_settings)

        pg = st.navigation(pages)
        pg.run()


if __name__ == "__main__":
    main()
