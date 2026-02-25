import extra_streamlit_components as stx
import streamlit as st

def get_cm():
    if "cm" not in st.session_state:
        st.session_state.cm = stx.CookieManager()
    return st.session_state.cm

c = get_cm()
st.write(c.get_all())
