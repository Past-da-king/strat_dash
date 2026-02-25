import streamlit as st
import extra_streamlit_components as stx

@st.cache_resource
def get_manager():
    return stx.CookieManager()

cm = get_manager()
st.write("Cookies:", cm.get_all())
st.write("Token:", cm.get("auth_token"))
