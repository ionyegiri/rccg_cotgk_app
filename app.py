"""
app.py — Entry point for the Church Rota App
Handles: page config, login, role-based navigation routing, logout.

Run with:  streamlit run app.py
"""

import yaml
import streamlit as st
import streamlit_authenticator as stauth
from yaml.loader import SafeLoader
from streamlit_authenticator.utilities import LoginError

# ── Page config (must be first Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="Church Rota App",
    page_icon="✝️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load credentials from config.yaml ────────────────────────────────────────
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.load(f, Loader=SafeLoader)

# ── Build authenticator ───────────────────────────────────────────────────────
authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

# Store authenticator in session state so pages can access it (e.g. for logout)
st.session_state["authenticator"] = authenticator
st.session_state["config"] = config

# ── Login form ────────────────────────────────────────────────────────────────
try:
    authenticator.login(location="main", key="church_app_login")
except LoginError as e:
    st.error(str(e))

# ── Route based on authentication status ─────────────────────────────────────
auth_status = st.session_state.get("authentication_status")
username    = st.session_state.get("username", "")
name        = st.session_state.get("name", "")

if auth_status is False:
    st.error("Username or password is incorrect.")
    st.stop()

elif auth_status is None:
    st.info("Please enter your username and password to continue.")
    st.stop()

# ── Authenticated — determine role ────────────────────────────────────────────
# Roles are stored in config.yaml under credentials.usernames.<user>.role
# Supported roles: "admin" | "editor" | "viewer"
user_role = (
    config["credentials"]["usernames"]
    .get(username, {})
    .get("role", "viewer")
)

st.session_state["role"] = user_role

# ── Build page list based on role ─────────────────────────────────────────────
common_pages = [
    st.Page("pages/5_My_Rota.py",        title="My Rota",       icon="📅"),
    st.Page("pages/1_Rota_Manager.py",   title="Rota Manager",  icon="🗓️"),
    st.Page("pages/3_Notifications.py",  title="Notifications", icon="🔔"),
]

editor_pages = [
    st.Page("pages/2_Members.py",        title="Members",       icon="👥"),
]

admin_pages = [
    st.Page("pages/4_Admin.py",          title="Admin",         icon="⚙️"),
]

if user_role == "admin":
    pages = common_pages + editor_pages + admin_pages
elif user_role == "editor":
    pages = common_pages + editor_pages
else:
    pages = [
        st.Page("pages/5_My_Rota.py",       title="My Rota",      icon="📅"),
        st.Page("pages/3_Notifications.py", title="Notifications", icon="🔔"),
    ]

# ── Sidebar: welcome message + logout ─────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### ✝️ Church Rota")
    st.markdown(f"Welcome, **{name}**")
    st.caption(f"Role: `{user_role}`")
    st.divider()
    authenticator.logout(button_name="Log out", location="sidebar", key="logout_btn")

# ── Run navigation ─────────────────────────────────────────────────────────────
pg = st.navigation(pages, position="sidebar")
pg.run()
