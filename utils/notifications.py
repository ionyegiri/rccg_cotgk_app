"""
utils/notifications.py — SendGrid email logic for rota notifications.

Secrets read from .streamlit/secrets.toml:
  SENDGRID_API_KEY = "SG.xxxx"
  SENDGRID_FROM_EMAIL = "rota@mychurch.org"
  SENDGRID_FROM_NAME  = "Church Rota"        # optional, defaults below
"""

import streamlit as st
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content


# ── Internal helper ───────────────────────────────────────────────────────────

def _get_sg_client() -> SendGridAPIClient:
    """Build a SendGrid client from Streamlit secrets."""
    return SendGridAPIClient(st.secrets["SENDGRID_API_KEY"])


def _from_email() -> Email:
    name  = st.secrets.get("SENDGRID_FROM_NAME")
    email = st.secrets["SENDGRID_FROM_EMAIL"]
    return Email(email, name)


# ── Single notification ───────────────────────────────────────────────────────

def send_rota_notification(
    to_email:     str,
    to_name:      str,
    service_date: str,
    service_type: str,
    rota_role:    str,
) -> tuple[bool, str]:
    """
    Send a single rota assignment email.

    Returns:
        (success: bool, message: str)
    """
    subject = f"You're on the rota — {service_date}"

    html_body = f"""
    <p>Hi {to_name},</p>
    <p>You have been added to the rota. Here are your details:</p>
    <table style="border-collapse:collapse; font-family:sans-serif;">
      <tr>
        <td style="padding:6px 16px 6px 0; font-weight:bold;">Date</td>
        <td style="padding:6px 0">{service_date}</td>
      </tr>
      <tr>
        <td style="padding:6px 16px 6px 0; font-weight:bold;">Service</td>
        <td style="padding:6px 0">{service_type}</td>
      </tr>
      <tr>
        <td style="padding:6px 16px 6px 0; font-weight:bold;">Your role</td>
        <td style="padding:6px 0">{rota_role}</td>
      </tr>
    </table>
    <p>If you have any questions please contact your rota coordinator.</p>
    <p>God bless,<br><strong>Church Rota Team</strong></p>
    """

    plain_body = (
        f"Hi {to_name},\n\n"
        f"You have been added to the rota:\n"
        f"  Date:     {service_date}\n"
        f"  Service:  {service_type}\n"
        f"  Role:     {rota_role}\n\n"
        f"If you have any questions please contact your rota coordinator.\n\n"
        f"God bless,\nChurch Rota Team"
    )

    message = Mail(
        from_email=_from_email(),
        to_emails=To(to_email, to_name),
        subject=subject,
        html_content=Content("text/html",  html_body),
        plain_text_content=Content("text/plain", plain_body),
    )

    try:
        sg = _get_sg_client()
        response = sg.send(message)
        if response.status_code in (200, 202):
            return True, f"Email sent to {to_name} ({to_email})"
        else:
            return False, f"Unexpected status {response.status_code} for {to_email}"
    except Exception as e:
      body = getattr(e, "body", None)
      return False, f"Failed to send to {to_email}: {str(e)} | body={body}"


# ── Bulk notifications ────────────────────────────────────────────────────────

def send_bulk_notifications(rota_entries: list[dict]) -> dict:
    """
    Send notification emails for a list of pending rota entries.

    Each entry must contain:
      members.email, members.full_name,
      service_date, service_type, rota_role

    Returns:
        {
          "sent":   [list of rota ids successfully emailed],
          "failed": [list of (rota_id, error_message) tuples],
        }
    """
    sent   = []
    failed = []

    for entry in rota_entries:
        member      = entry.get("members", {})
        to_email    = member.get("email", "")
        to_name     = member.get("full_name", "Volunteer")
        rota_id     = entry["id"]
        service_date = entry["service_date"]
        service_type = entry["service_type"]
        rota_role    = entry["rota_role"]

        if not to_email:
            failed.append((rota_id, "No email address on record"))
            continue

        success, message = send_rota_notification(
            to_email=to_email,
            to_name=to_name,
            service_date=service_date,
            service_type=service_type,
            rota_role=rota_role,
        )

        if success:
            sent.append(rota_id)
        else:
            failed.append((rota_id, message))

    return {"sent": sent, "failed": failed}


# ── Reminder email ────────────────────────────────────────────────────────────

def send_reminder(
    to_email:     str,
    to_name:      str,
    service_date: str,
    service_type: str,
    rota_role:    str,
) -> tuple[bool, str]:
    """
    Send a reminder email for an upcoming rota slot.
    Same signature as send_rota_notification but with a different subject line.
    """
    subject = f"Reminder: you're on the rota this {service_date}"

    html_body = f"""
    <p>Hi {to_name},</p>
    <p>This is a friendly reminder that you are on the rota soon:</p>
    <table style="border-collapse:collapse; font-family:sans-serif;">
      <tr>
        <td style="padding:6px 16px 6px 0; font-weight:bold;">Date</td>
        <td style="padding:6px 0">{service_date}</td>
      </tr>
      <tr>
        <td style="padding:6px 16px 6px 0; font-weight:bold;">Service</td>
        <td style="padding:6px 0">{service_type}</td>
      </tr>
      <tr>
        <td style="padding:6px 16px 6px 0; font-weight:bold;">Your role</td>
        <td style="padding:6px 0">{rota_role}</td>
      </tr>
    </table>
    <p>God bless,<br><strong>Church Rota Team</strong></p>
    """

    plain_body = (
        f"Hi {to_name},\n\n"
        f"Reminder — you are on the rota:\n"
        f"  Date:     {service_date}\n"
        f"  Service:  {service_type}\n"
        f"  Role:     {rota_role}\n\n"
        f"God bless,\nChurch Rota Team"
    )

    message = Mail(
        from_email=_from_email(),
        to_emails=To(to_email, to_name),
        subject=subject,
        html_content=Content("text/html",  html_body),
        plain_text_content=Content("text/plain", plain_body),
    )

    try:
        sg = _get_sg_client()
        response = sg.send(message)
        if response.status_code in (200, 202):
            return True, f"Reminder sent to {to_name} ({to_email})"
        else:
            return False, f"Unexpected status {response.status_code} for {to_email}"
    except Exception as e:
        return False, f"Failed to send reminder to {to_email}: {str(e)}"
