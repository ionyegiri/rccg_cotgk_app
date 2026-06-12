"""
pages/1_Rota_Manager.py — Create, view, and delete rota entries.
Accessible to: admin, editor
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from utils.db import (
    get_all_rota_entries,
    get_all_members,
    add_rota_entry,
    delete_rota_entry,
)

# ── Auth guard ────────────────────────────────────────────────────────────────
if not st.session_state.get("authentication_status"):
    st.stop()

role = st.session_state.get("role", "viewer")
if role not in ("admin", "editor"):
    st.error("⛔ You do not have permission to access this page.")
    st.stop()

# ── Page ──────────────────────────────────────────────────────────────────────
st.title("🗓️ Rota Manager")
st.caption("Create, view and remove rota assignments.")

SERVICE_TYPES = ["Sunday Morning", "Sunday Evening", "Wednesday Evening", "Special Event"]
ROTA_ROLES    = ["Preacher", "Worship Leader", "Sound", "Projection", "Greeter",
                 "Children's Worker", "Communion Steward", "Prayer Leader", "Other"]

# ── Add new entry ─────────────────────────────────────────────────────────────
with st.expander("➕ Add new rota entry", expanded=True):
    members = get_all_members()
    if not members:
        st.warning("No members found. Add members first in the Members page.")
    else:
        member_map = {m["full_name"]: m["id"] for m in members}

        col1, col2 = st.columns(2)
        with col1:
            selected_name = st.selectbox("Member", options=list(member_map.keys()))
            service_date  = st.date_input(
                "Service date",
                value=date.today() + timedelta(days=(6 - date.today().weekday())),  # next Sunday
                min_value=date.today(),
            )
        with col2:
            service_type = st.selectbox("Service type", options=SERVICE_TYPES)
            rota_role    = st.selectbox("Role", options=ROTA_ROLES)

        if st.button("Add to rota", type="primary", use_container_width=True):
            try:
                add_rota_entry(
                    member_id=member_map[selected_name],
                    service_date=str(service_date),
                    service_type=service_type,
                    rota_role=rota_role,
                )
                st.success(f"✅ {selected_name} added to rota for {service_date} ({rota_role})")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to add entry: {e}")

st.divider()

# ── View / filter rota ────────────────────────────────────────────────────────
st.subheader("Current Rota")

entries = get_all_rota_entries()

if not entries:
    st.info("No rota entries yet. Use the form above to add some.")
else:
    # Build display dataframe
    rows = []
    for e in entries:
        member_info = e.get("members") or {}
        rows.append({
            "ID":       e["id"],
            "Date":     e["service_date"],
            "Service":  e["service_type"],
            "Role":     e["rota_role"],
            "Member":   member_info.get("full_name", "—"),
            "Notified": "✅" if e["notified"] else "⏳",
        })

    df = pd.DataFrame(rows)

    # Filter controls
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_service = st.selectbox("Filter by service", ["All"] + SERVICE_TYPES)
    with col2:
        filter_role = st.selectbox("Filter by role", ["All"] + ROTA_ROLES)
    with col3:
        filter_notified = st.selectbox("Filter by notification", ["All", "Notified ✅", "Pending ⏳"])

    filtered = df.copy()
    if filter_service != "All":
        filtered = filtered[filtered["Service"] == filter_service]
    if filter_role != "All":
        filtered = filtered[filtered["Role"] == filter_role]
    if filter_notified == "Notified ✅":
        filtered = filtered[filtered["Notified"] == "✅"]
    elif filter_notified == "Pending ⏳":
        filtered = filtered[filtered["Notified"] == "⏳"]

    st.dataframe(
        filtered.drop(columns=["ID"]),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(f"Showing {len(filtered)} of {len(df)} entries")

    st.divider()

    # ── Delete entry ──────────────────────────────────────────────────────────
    st.subheader("🗑️ Delete a rota entry")
    st.caption("Select an entry by its row number to remove it.")

    entry_options = {
        f"{row['Date']} — {row['Member']} — {row['Role']}": row["ID"]
        for _, row in df.iterrows()
    }

    selected_label = st.selectbox("Select entry to delete", options=list(entry_options.keys()))
    selected_id    = entry_options[selected_label]

    if st.button("Delete entry", type="secondary", use_container_width=True):
        try:
            delete_rota_entry(selected_id)
            st.success(f"🗑️ Entry deleted: {selected_label}")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to delete: {e}")
