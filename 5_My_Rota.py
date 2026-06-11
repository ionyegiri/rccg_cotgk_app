"""
pages/5_My_Rota.py — Personal rota view for every logged-in user.
Accessible to: all authenticated users (admin, editor, viewer)
"""

import streamlit as st
import pandas as pd
from datetime import date
from utils.db import get_rota_by_username

# ── Auth guard ────────────────────────────────────────────────────────────────
if not st.session_state.get("authentication_status"):
    st.stop()

# ── Page ──────────────────────────────────────────────────────────────────────
username = st.session_state.get("username", "")
name     = st.session_state.get("name", "")

st.title("📅 My Rota")
st.caption(f"All upcoming and past rota assignments for **{name}**.")

entries = get_rota_by_username(username)

if not entries:
    st.info(
        "You have no rota entries yet. "
        "Your rota coordinator will add you when you're scheduled."
    )
else:
    rows = []
    for e in entries:
        rows.append({
            "Date":    e["service_date"],
            "Service": e["service_type"],
            "Role":    e["rota_role"],
            "Status":  "Notified ✅" if e["notified"] else "Pending ⏳",
        })

    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"]).dt.date

    today = date.today()

    # ── Upcoming ──────────────────────────────────────────────────────────────
    upcoming = df[df["Date"] >= today].sort_values("Date")
    st.subheader(f"Upcoming ({len(upcoming)})")

    if upcoming.empty:
        st.info("No upcoming assignments.")
    else:
        next_entry = upcoming.iloc[0]
        col1, col2, col3 = st.columns(3)
        col1.metric("Next date",  str(next_entry["Date"]))
        col2.metric("Service",    next_entry["Service"])
        col3.metric("Your role",  next_entry["Role"])

        st.divider()

        st.dataframe(
            upcoming.reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    # ── Past ──────────────────────────────────────────────────────────────────
    past = df[df["Date"] < today].sort_values("Date", ascending=False)
    st.subheader(f"Past assignments ({len(past)})")

    if past.empty:
        st.info("No past assignments on record.")
    else:
        with st.expander("Show past assignments"):
            st.dataframe(
                past.reset_index(drop=True),
                use_container_width=True,
                hide_index=True,
            )
