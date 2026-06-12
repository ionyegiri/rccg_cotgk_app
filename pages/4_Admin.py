"""
pages/4_Admin.py — Admin-only settings and app management.
Accessible to: admin only
"""

import yaml
import streamlit as st
import bcrypt
from yaml.loader import SafeLoader

# ── Auth guard ────────────────────────────────────────────────────────────────
if not st.session_state.get("authentication_status"):
    st.stop()

if st.session_state.get("role") != "admin":
    st.error("⛔ This page is restricted to admins only.")
    st.stop()

# ── Page ──────────────────────────────────────────────────────────────────────
st.title("⚙️ Admin")
st.caption("App settings, user management and maintenance tools.")

config      = st.session_state.get("config", {})
credentials = config.get("credentials", {}).get("usernames", {})

# ── Current users overview ────────────────────────────────────────────────────
st.subheader("👤 Registered login accounts")
st.caption("These are the accounts in `config.yaml` that can log in to the app.")

if credentials:
    rows = []
    for uname, data in credentials.items():
        rows.append({
            "Username": uname,
            "Name":     f"{data.get('first_name','')} {data.get('last_name','')}".strip(),
            "Email":    data.get("email", "—"),
            "Role":     data.get("role", "viewer"),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)
else:
    st.info("No users found in config.yaml.")

st.divider()

# ── Password hash generator ───────────────────────────────────────────────────
st.subheader("🔐 Generate a hashed password")
st.caption(
    "Use this to create a bcrypt hash for a new user's password. "
    "Copy the hash into `config.yaml` under the user's `password:` field."
)

plain_pw = st.text_input(
    "Enter plain-text password to hash",
    type="password",
    placeholder="e.g. MySecurePass123!",
    key="hash_input",
)

if st.button("Generate hash", type="primary"):
    if not plain_pw:
        st.warning("Please enter a password first.")
    elif len(plain_pw) < 8:
        st.warning("Password should be at least 8 characters.")
    else:
        hashed = bcrypt.hashpw(plain_pw.encode(), bcrypt.gensalt()).decode()
        st.code(hashed, language=None)
        st.caption("Copy this hash into `config.yaml` as the `password:` value for the user.")

st.divider()

# ── config.yaml viewer ────────────────────────────────────────────────────────
st.subheader("📄 Current config.yaml structure")
st.caption("Read-only view. Edit the file directly on the server to make changes.")

with st.expander("View config.yaml (passwords hidden)"):
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            raw = yaml.load(f, Loader=SafeLoader)
        safe  = yaml.dump(raw, default_flow_style=False)
        lines = []
        for line in safe.splitlines():
            if "password:" in line.lower():
                lines.append("  password: ••••••••••••  # hidden")
            else:
                lines.append(line)
        st.code("\n".join(lines), language="yaml")
    except Exception as e:
        st.error(f"Could not read config.yaml: {e}")

st.divider()

# ── Cookie settings overview ──────────────────────────────────────────────────
st.subheader("🍪 Cookie / session settings")

cookie_cfg = config.get("cookie", {})
col1, col2, col3 = st.columns(3)
col1.metric("Cookie name",   cookie_cfg.get("name", "—"))
col2.metric("Expiry (days)", cookie_cfg.get("expiry_days", "—"))
col3.metric("Key set?",      "✅ Yes" if cookie_cfg.get("key") else "❌ No")

st.caption(
    "To change these values edit `config.yaml` directly and restart the app. "
    "Generate a strong random cookie key with: "
    "`python3 -c \"import secrets; print(secrets.token_hex(32))\"`"
)

st.divider()

# ── Danger zone ───────────────────────────────────────────────────────────────
st.subheader("⚠️ Danger zone")

with st.expander("Show danger zone actions"):
    st.warning(
        "The actions below are destructive. "
        "They cannot be undone without restoring from a Supabase backup."
    )
    st.markdown("**Clear all pending notification flags**")
    st.caption(
        "Marks every rota entry as `notified=True`. "
        "Use only if you need to reset the notification queue."
    )
    if st.button("Reset all notification flags", type="secondary"):
        st.info(
            "To implement this, run in the Supabase SQL editor: "
            "`UPDATE rota SET notified = true;` "
            "Intentionally not wired up here to prevent accidental use."
        )
