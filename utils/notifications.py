"""
utils/notifications.py — Resend email helpers.

Provides:
- Single rota-assignment notifications
- Bulk notifications for multiple rota entries
- Reminder emails for upcoming assignments
- Safe, per-recipient result reporting

Required Streamlit secrets:

[resend]
api_key = "re_..."
from_email = "rota@your-verified-domain.org"
from_name = "Church Rota"

Optional:
[church]
name = "Your Church"

Keep .streamlit/secrets.toml out of Git. Add these values to Streamlit
Community Cloud's Secrets settings instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Iterable, Mapping, Sequence

import resend
import streamlit as st


@dataclass(frozen=True)
class NotificationResult:
    """Result for one attempted email."""

    recipient: str
    success: bool
    message: str
    email_id: str | None = None


# ── Configuration ──────────────────────────────────────────────────────────────


def _resend_config() -> tuple[str, str, str, str]:
    """Read Resend configuration from Streamlit secrets."""
    resend_section = st.secrets["resend"]
    api_key = str(resend_section["api_key"])
    from_email = str(resend_section["from_email"])
    from_name = str(resend_section.get("from_name", "Church Rota"))
    church_name = str(st.secrets.get("church", {}).get("name", from_name))

    if not api_key or api_key.startswith("your-"):
        raise ValueError("A valid Resend API key is missing from st.secrets.")
    if not from_email:
        raise ValueError("resend.from_email is missing from st.secrets.")

    return api_key, from_email, from_name, church_name


def _configure_resend() -> tuple[str, str, str]:
    """Configure the Resend SDK and return sender details."""
    api_key, from_email, from_name, church_name = _resend_config()
    resend.api_key = api_key
    return from_email, from_name, church_name


# ── Formatting ─────────────────────────────────────────────────────────────────


def _format_date(value: Any) -> str:
    """Convert date-like values into a readable date."""
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime("%A, %-d %B %Y")

    raw_value = str(value)
    try:
        return date.fromisoformat(raw_value[:10]).strftime("%A, %-d %B %Y")
    except ValueError:
        return raw_value


def _assignment_lines(assignments: Sequence[Mapping[str, Any]]) -> str:
    """Create plain-text lines for one or more rota assignments."""
    lines: list[str] = []
    for assignment in assignments:
        lines.append(
            "  Date:    {date}\n"
            "  Service: {service}\n"
            "  Role:    {role}".format(
                date=_format_date(assignment.get("service_date", "")),
                service=assignment.get("service_type", ""),
                role=assignment.get("role", ""),
            )
        )
    return "\n\n".join(lines)


def _email_result(recipient: str, response: Any) -> NotificationResult:
    """Normalise a successful Resend response."""
    email_id = None
    if isinstance(response, Mapping):
        email_id = response.get("id")
    else:
        email_id = getattr(response, "id", None)

    return NotificationResult(
        recipient=recipient,
        success=True,
        message="Email sent successfully.",
        email_id=email_id,
    )


# ── Single assignment notification ────────────────────────────────────────────


def send_rota_notification(
    to_email: str,
    member_name: str,
    service_date: Any,
    service_type: str,
    role: str,
) -> tuple[bool, str]:
    """Send one assignment notification.

    This keeps the original function signature used by Rota Manager.
    """
    result = send_assignment_email(
        to_email=to_email,
        member_name=member_name,
        assignments=[
            {
                "service_date": service_date,
                "service_type": service_type,
                "role": role,
            }
        ],
        email_kind="assignment",
    )
    return result.success, result.message


def send_assignment_email(
    to_email: str,
    member_name: str,
    assignments: Sequence[Mapping[str, Any]],
    email_kind: str = "assignment",
) -> NotificationResult:
    """Send one email containing one or more rota assignments."""
    try:
        from_email, from_name, church_name = _configure_resend()
        assignment_text = _assignment_lines(assignments)

        if email_kind == "reminder":
            subject = f"Rota reminder — {church_name}"
            opening = f"This is a reminder about your upcoming rota assignment{'' if len(assignments) == 1 else 's'}."
            closing = "Please contact the rota team as soon as possible if you need a swap."
        else:
            subject = f"You have been added to the {church_name} rota"
            opening = f"You have been scheduled for the following rota assignment{'' if len(assignments) == 1 else 's'}:"
            closing = "Please reply if you need to arrange a swap."

        body = f"""Hi {member_name},

{opening}

{assignment_text}

{closing}

God bless,
{church_name} Rota Team
""".strip()

        response = resend.Emails.send(
            {
                "from": f"{from_name} <{from_email}>",
                "to": [to_email],
                "subject": subject,
                "text": body,
            }
        )
        return _email_result(to_email, response)

    except Exception as exc:
        return NotificationResult(
            recipient=to_email,
            success=False,
            message=str(exc),
        )


# ── Bulk notifications ────────────────────────────────────────────────────────


def send_bulk_notifications(
    notifications: Iterable[Mapping[str, Any]],
) -> list[NotificationResult]:
    """Send assignment emails to multiple recipients.

    Each item must contain:
        to_email, member_name, assignments

    Example:
        send_bulk_notifications([
            {
                "to_email": "jane@example.org",
                "member_name": "Jane Wilson",
                "assignments": [entry],
            }
        ])

    Returns one NotificationResult per recipient. A failure for one person
    does not stop the remaining emails from being attempted.
    """
    results: list[NotificationResult] = []

    for item in notifications:
        results.append(
            send_assignment_email(
                to_email=str(item["to_email"]),
                member_name=str(item["member_name"]),
                assignments=list(item["assignments"]),
                email_kind=str(item.get("email_kind", "assignment")),
            )
        )

    return results


def send_bulk_rota_notifications(
    entries: Sequence[Mapping[str, Any]],
    members_by_username: Mapping[str, Mapping[str, Any]],
) -> list[NotificationResult]:
    """Group rota entries by member and send one email per member.

    This avoids sending five separate messages when one member has five
    assignments. Each entry must contain assigned_to, service_date,
    service_type, and role. The member record must contain name and email.
    """
    grouped: dict[str, list[Mapping[str, Any]]] = {}

    for entry in entries:
        username = str(entry["assigned_to"])
        grouped.setdefault(username, []).append(entry)

    notifications: list[dict[str, Any]] = []
    for username, member_entries in grouped.items():
        member = members_by_username.get(username)
        if not member:
            notifications.append(
                {
                    "to_email": username,
                    "member_name": username,
                    "assignments": [],
                    "email_kind": "assignment",
                }
            )
            continue

        notifications.append(
            {
                "to_email": member["email"],
                "member_name": member["name"],
                "assignments": member_entries,
                "email_kind": "assignment",
            }
        )

    return send_bulk_notifications(notifications)


# ── Reminder emails ────────────────────────────────────────────────────────────


def send_reminder_email(
    to_email: str,
    member_name: str,
    assignments: Sequence[Mapping[str, Any]],
) -> NotificationResult:
    """Send a reminder email for one or more upcoming assignments."""
    return send_assignment_email(
        to_email=to_email,
        member_name=member_name,
        assignments=assignments,
        email_kind="reminder",
    )


def send_bulk_reminders(
    entries: Sequence[Mapping[str, Any]],
    members_by_username: Mapping[str, Mapping[str, Any]],
) -> list[NotificationResult]:
    """Group upcoming entries by member and send one reminder per member."""
    grouped: dict[str, list[Mapping[str, Any]]] = {}

    for entry in entries:
        username = str(entry["assigned_to"])
        grouped.setdefault(username, []).append(entry)

    results: list[NotificationResult] = []
    for username, member_entries in grouped.items():
        member = members_by_username.get(username)
        if not member:
            results.append(
                NotificationResult(
                    recipient=username,
                    success=False,
                    message="No member record found for this username.",
                )
            )
            continue

        results.append(
            send_reminder_email(
                to_email=member["email"],
                member_name=member["name"],
                assignments=member_entries,
            )
        )

    return results


# ── Reporting and database status ─────────────────────────────────────────────


def summarise_results(results: Sequence[NotificationResult]) -> dict[str, int]:
    """Return counts suitable for Streamlit metrics."""
    sent = sum(result.success for result in results)
    failed = len(results) - sent
    return {"attempted": len(results), "sent": sent, "failed": failed}


def mark_as_notified(entry_id: int) -> None:
    """Mark a rota entry as notified after successful delivery."""
    from utils.db import get_client

    get_client().table("rota").update({"notified": True}).eq("id", entry_id).execute()


def mark_entries_as_notified(
    entry_ids: Iterable[int],
) -> None:
    """Mark several rota entries as notified."""
    from utils.db import get_client

    client = get_client()
    for entry_id in entry_ids:
        client.table("rota").update({"notified": True}).eq("id", entry_id).execute()
