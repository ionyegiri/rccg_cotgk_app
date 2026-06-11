"""
pages/2_Members.py — Add and manage church members.
Accessible to: admin, editor
"""

import streamlit as st
import pandas as pd
from utils.db import (
    get_all_members,
    add_member,
    update_member,
    deactivate_member,
)

# ── Auth guard ────────────────────────────────────────────────────────────────
if not st.session_state.get("authentication_status"):
    st.stop()

role = st.session_state.get("role", "viewer")
if role not in ("admin", "editor"):
    st.error("⛔ You do not have permission to access this page.")
    st.stop()

# ── Page ──────────────────────────────────────────────────────────────────────
st.title("👥 Members")
st.caption("Add, edit and deactivate church members.")

ROLES = ["viewer", "editor", "admin"]

# ── Add new member ─────────────────────────────────────────────────────────────
with st.expander("➕ Add new member", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        new_full_name = st.text_input("Full name",     key="add_full_name")
        new_username  = st.text_input("Login username (no spaces)", key="add_username")
        new_role      = st.selectbox("App role", options=ROLES, key="add_role")
    with col2:
        new_email = st.text_input("Email address", key="add_email")
        new_phone = st.text_input("Phone number (optional)", key="add_phone")

    st.caption(
        "⚠️ After adding a member here, also add their hashed password to `config.yaml` "
        "so they can log in."
    )

    if st.button("Add member", type="primary", use_container_width=True):
        if not new_full_name or not new_username or not new_email:
            st.warning("Full name, username and email are required.")
        elif " " in new_username:
            st.warning("Username must not contain spaces.")
        else:
            existing = [m["username"] for m in get_all_members()]
            if new_username in existing:
                st.error(f"Username '{new_username}' is already taken.")
            else:
                try:
                    add_member(
                        full_name=new_full_name,
                        username=new_username,
                        email=new_email,
                        phone=new_phone,
                        role=new_role,
                    )
                    st.success(f"✅ {new_full_name} added successfully.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add member: {e}")

st.divider()

# ── Member list ───────────────────────────────────────────────────────────────
st.subheader("All Members")

members = get_all_members()

if not members:
    st.info("No active members found. Use the form above to add the first one.")
else:
    rows = [{
        "ID":       m["id"],
        "Name":     m["full_name"],
        "Username": m["username"],
        "Email":    m["email"],
        "Phone":    m.get("phone") or "—",
        "Role":     m["role"],
    } for m in members]

    df = pd.DataFrame(rows)

    search = st.text_input("🔍 Search members", placeholder="Type a name or email...")
    if search:
        mask = (
            df["Name"].str.contains(search, case=False, na=False) |
            df["Email"].str.contains(search, case=False, na=False) |
            df["Username"].str.contains(search, case=False, na=False)
        )
        df_display = df[mask]
    else:
        df_display = df

    st.dataframe(
        df_display.drop(columns=["ID"]),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(f"{len(df_display)} member(s) shown")

    st.divider()

    # ── Edit member ───────────────────────────────────────────────────────────
    st.subheader("✏️ Edit a member")

    member_options = {m["full_name"]: m for m in members}
    selected_name  = st.selectbox("Select member to edit", options=list(member_options.keys()))
    selected       = member_options[selected_name]

    col1, col2 = st.columns(2)
    with col1:
        edit_full_name = st.text_input("Full name",    value=selected["full_name"], key="edit_name")
        edit_email     = st.text_input("Email",        value=selected["email"],     key="edit_email")
        edit_role      = st.selectbox("App role", options=ROLES,
                                      index=ROLES.index(selected["role"]),          key="edit_role")
    with col2:
        edit_phone = st.text_input("Phone", value=selected.get("phone") or "",      key="edit_phone")

    if st.button("Save changes", type="primary", use_container_width=True):
        try:
            update_member(selected["id"], {
                "full_name": edit_full_name,
                "email":     edit_email,
                "phone":     edit_phone,
                "role":      edit_role,
            })
            st.success(f"✅ {edit_full_name} updated.")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to update: {e}")

    st.divider()

    # ── Deactivate member ─────────────────────────────────────────────────────
    st.subheader("🚫 Deactivate a member")
    st.caption("Deactivating hides the member from rotas but keeps historical data intact.")

    deactivate_options = {m["full_name"]: m["id"] for m in members}
    deactivate_name    = st.selectbox(
        "Select member to deactivate",
        options=list(deactivate_options.keys()),
        key="deactivate_select",
    )

    if role != "admin":
        st.info("Only admins can deactivate members.")
    else:
        confirm = st.checkbox(f"I confirm I want to deactivate **{deactivate_name}**")
        if st.button("Deactivate member", type="secondary",
                     disabled=not confirm, use_container_width=True):
            try:
                deactivate_member(deactivate_options[deactivate_name])
                st.success(f"🚫 {deactivate_name} has been deactivated.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to deactivate: {e}")
