"""
pages/3_Notifications.py — Send pending rota notification emails.
Accessible to: admin, editor
"""

import streamlit as st
import pandas as pd
from utils.db import (
    get_pending_notifications,
    mark_all_notified,
    mark_notified,
)
from utils.notifications import send_bulk_notifications, send_reminder

# ── Auth guard ────────────────────────────────────────────────────────────────
if not st.session_state.get("authentication_status"):
    st.stop()

role = st.session_state.get("role", "viewer")
if role not in ("admin", "editor"):
    st.error("⛔ You do not have permission to access this page.")
    st.stop()

# ── Page ──────────────────────────────────────────────────────────────────────
st.title("🔔 Notifications")
st.caption("Send rota assignment emails to members who haven't been notified yet.")

# ── Pending notifications ─────────────────────────────────────────────────────
pending = get_pending_notifications()

if not pending:
    st.success("✅ All rota members have been notified. Nothing pending.")
else:
    st.info(f"**{len(pending)}** pending notification(s) to send.")

    rows = []
    for e in pending:
        member = e.get("members") or {}
        rows.append({
            "ID":      e["id"],
            "Date":    e["service_date"],
            "Service": e["service_type"],
            "Role":    e["rota_role"],
            "Member":  member.get("full_name", "—"),
            "Email":   member.get("email", "—"),
        })

    df = pd.DataFrame(rows)

    st.dataframe(
        df.drop(columns=["ID"]),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    #--- Temporary Debug-----#
    st.write("SENDGRID key present:", bool(st.secrets.get("SENDGRID_API_KEY")))
    st.write("SENDGRID key prefix:", st.secrets.get("SENDGRID_API_KEY", "")[:5])
    # ── Send all pending ──────────────────────────────────────────────────────
    st.subheader("📨 Send all pending notifications")
    st.caption("This will email every member in the table above.")

    if st.button("Send all notifications", type="primary", use_container_width=True):
        with st.spinner("Sending emails…"):
            results = send_bulk_notifications(pending)

        sent_ids   = results["sent"]
        failed_ids = results["failed"]

        if sent_ids:
            mark_all_notified(sent_ids)
            st.success(f"✅ {len(sent_ids)} email(s) sent successfully.")

        if failed_ids:
            st.error(f"❌ {len(failed_ids)} email(s) failed:")
            for rota_id, reason in failed_ids:
                entry = next((e for e in pending if e["id"] == rota_id), {})
                member_name = (entry.get("members") or {}).get("full_name", f"ID {rota_id}")
                st.write(f"  • {member_name}: {reason}")

        if sent_ids or failed_ids:
            st.rerun()

    st.divider()

    # ── Send individual notification ──────────────────────────────────────────
    st.subheader("✉️ Send to one person")
    st.caption("Choose a single pending entry to notify individually.")

    entry_options = {
        f"{row['Date']} — {row['Member']} ({row['Role']})": idx
        for idx, row in df.iterrows()
    }

    selected_label = st.selectbox("Select entry", options=list(entry_options.keys()))
    selected_row   = df.iloc[entry_options[selected_label]]

    if st.button("Send this notification", type="secondary", use_container_width=True):
        entry  = pending[entry_options[selected_label]]
        member = entry.get("members") or {}
        with st.spinner(f"Sending to {member.get('full_name', '')}…"):
            from utils.notifications import send_rota_notification
            success, msg = send_rota_notification(
                to_email=member.get("email", ""),
                to_name=member.get("full_name", "Volunteer"),
                service_date=entry["service_date"],
                service_type=entry["service_type"],
                rota_role=entry["rota_role"],
            )
        if success:
            mark_notified(entry["id"])
            st.success(f"✅ {msg}")
            st.rerun()
        else:
            st.error(f"❌ {msg}")

    st.divider()

    # ── Send reminders ────────────────────────────────────────────────────────
    st.subheader("⏰ Send a reminder")
    st.caption(
        "Reminders can be sent to already-notified members. "
        "Select from the full rota on the Rota Manager page — "
        "use this to re-notify a specific person."
    )

    reminder_options = {
        f"{row['Date']} — {row['Member']} ({row['Role']})": idx
        for idx, row in df.iterrows()
    }

    reminder_label = st.selectbox(
        "Select entry to remind",
        options=list(reminder_options.keys()),
        key="reminder_select",
    )

    if st.button("Send reminder", type="secondary", use_container_width=True):
        entry  = pending[reminder_options[reminder_label]]
        member = entry.get("members") or {}
        with st.spinner(f"Sending reminder to {member.get('full_name', '')}…"):
            success, msg = send_reminder(
                to_email=member.get("email", ""),
                to_name=member.get("full_name", "Volunteer"),
                service_date=entry["service_date"],
                service_type=entry["service_type"],
                rota_role=entry["rota_role"],
            )
        if success:
            st.success(f"✅ {msg}")
        else:
            st.error(f"❌ {msg}")
