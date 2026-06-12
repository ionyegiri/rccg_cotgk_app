"""
utils/db.py — All Supabase database queries in one place.

Expected Supabase tables:
  members  (id, username, full_name, email, phone, role, active, created_at)
  rota     (id, member_id, service_date, service_type, rota_role, notified, created_at)

Secrets read from .streamlit/secrets.toml:
  SUPABASE_URL = "https://xxxx.supabase.co"
  SUPABASE_KEY = "eyJ..."
"""

import streamlit as st
from supabase import create_client, Client


# ── Client (cached for the lifetime of the Streamlit session) ────────────────

@st.cache_resource
def get_client() -> Client:
    """Create and cache a single Supabase client."""
    url = st.secrets[SUPABASE_URL]
    key = st.secrets[SUPABASE_KEY]
    return create_client(url, key)


# ── MEMBERS ───────────────────────────────────────────────────────────────────

def get_all_members() -> list[dict]:
    """Return all active members ordered by full_name."""
    client = get_client()
    response = (
        client.table("members")
        .select("*")
        .eq("active", True)
        .order("full_name")
        .execute()
    )
    return response.data


def get_member_by_username(username: str) -> dict | None:
    """Return a single member record matching a login username."""
    client = get_client()
    response = (
        client.table("members")
        .select("*")
        .eq("username", username)
        .single()
        .execute()
    )
    return response.data


def add_member(full_name: str, username: str, email: str,
               phone: str, role: str) -> dict:
    """Insert a new member and return the created row."""
    client = get_client()
    response = (
        client.table("members")
        .insert({
            "full_name": full_name,
            "username":  username,
            "email":     email,
            "phone":     phone,
            "role":      role,
            "active":    True,
        })
        .select()
        .execute()
    )
    return response.data[0]


def update_member(member_id: int, updates: dict) -> dict:
    """Update fields on a member row. Pass only changed fields in updates."""
    client = get_client()
    response = (
        client.table("members")
        .update(updates)
        .eq("id", member_id)
        .select()
        .execute()
    )
    return response.data[0]


def deactivate_member(member_id: int) -> None:
    """Soft-delete: set active=False instead of deleting the row."""
    client = get_client()
    client.table("members").update({"active": False}).eq("id", member_id).execute()


# ── ROTA ──────────────────────────────────────────────────────────────────────

def get_all_rota_entries() -> list[dict]:
    """Return all rota entries joined with member names, ordered by date."""
    client = get_client()
    response = (
        client.table("rota")
        .select("*, members(full_name, email)")
        .order("service_date")
        .execute()
    )
    return response.data


def get_rota_by_member(member_id: int) -> list[dict]:
    """Return all rota entries for a specific member (for My Rota page)."""
    client = get_client()
    response = (
        client.table("rota")
        .select("*, members(full_name, email)")
        .eq("member_id", member_id)
        .order("service_date")
        .execute()
    )
    return response.data


def get_rota_by_username(username: str) -> list[dict]:
    """Convenience: look up member first, then return their rota entries."""
    member = get_member_by_username(username)
    if not member:
        return []
    return get_rota_by_member(member["id"])


def get_pending_notifications() -> list[dict]:
    """Return rota entries where notified=False (email not yet sent)."""
    client = get_client()
    response = (
        client.table("rota")
        .select("*, members(full_name, email)")
        .eq("notified", False)
        .order("service_date")
        .execute()
    )
    return response.data


def add_rota_entry(member_id: int, service_date: str,
                   service_type: str, rota_role: str) -> dict:
    """
    Insert a new rota entry.
    service_date format: 'YYYY-MM-DD'
    service_type examples: 'Sunday Morning', 'Wednesday Evening'
    rota_role examples: 'Worship Leader', 'Sound', 'Greeter', 'Preacher'
    """
    client = get_client()
    response = (
        client.table("rota")
        .insert({
            "member_id":    member_id,
            "service_date": service_date,
            "service_type": service_type,
            "rota_role":    rota_role,
            "notified":     False,
        })
        .select()
        .execute()
    )
    return response.data[0]


def delete_rota_entry(rota_id: int) -> None:
    """Permanently delete a rota entry by its id."""
    client = get_client()
    client.table("rota").delete().eq("id", rota_id).execute()


def mark_notified(rota_id: int) -> None:
    """Set notified=True after a notification email has been sent."""
    client = get_client()
    client.table("rota").update({"notified": True}).eq("id", rota_id).execute()


def mark_all_notified(rota_ids: list[int]) -> None:
    """Bulk mark a list of rota entry ids as notified."""
    client = get_client()
    client.table("rota").update({"notified": True}).in_("id", rota_ids).execute()
