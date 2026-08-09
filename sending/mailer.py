"""
Sends a single email through a connected SendingAccount, using the Gmail API
or Microsoft Graph API directly (REST), refreshing the access token first if
it's expired.

This is called per-recipient by campaigns/sending_engine.py. It intentionally
raises on failure — the caller is responsible for catching per-recipient
errors and recording them on CampaignRecipient, so one bad address doesn't
stop the rest of the campaign.
"""
import base64
from email.mime.text import MIMEText

import requests
from django.utils import timezone

from . import oauth


class SendError(Exception):
    pass


def _ensure_fresh_token(account):
    """Refresh the access token if it's missing/expired, persisting the new one."""
    if account.access_token and account.token_expires_at and account.token_expires_at > timezone.now():
        return account.access_token

    if not account.refresh_token:
        account.status = account.Status.NEEDS_REAUTH
        account.save(update_fields=["status"])
        raise SendError(f"{account.sender_email} needs to be reconnected (no refresh token on file).")

    try:
        tokens = oauth.refresh_access_token(account.provider, account.refresh_token)
    except Exception as exc:
        account.status = account.Status.NEEDS_REAUTH
        account.save(update_fields=["status"])
        raise SendError(f"Couldn't refresh token for {account.sender_email}: {exc}") from exc

    from datetime import timedelta

    account.access_token = tokens.get("access_token", "")
    account.token_expires_at = timezone.now() + timedelta(seconds=tokens.get("expires_in", 3600))
    account.save(update_fields=["access_token", "token_expires_at"])
    return account.access_token


def _send_via_gmail(account, to_email, subject, body, is_html):
    access_token = _ensure_fresh_token(account)
    mime = MIMEText(body, "html" if is_html else "plain")
    mime["to"] = to_email
    mime["from"] = account.sender_email
    mime["subject"] = subject
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()

    resp = requests.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={"raw": raw},
        timeout=20,
    )
    if resp.status_code >= 400:
        raise SendError(f"Gmail API error {resp.status_code}: {resp.text[:300]}")


def _send_via_microsoft(account, to_email, subject, body, is_html):
    access_token = _ensure_fresh_token(account)
    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML" if is_html else "Text", "content": body},
            "toRecipients": [{"emailAddress": {"address": to_email}}],
        },
        "saveToSentItems": "true",
    }
    resp = requests.post(
        "https://graph.microsoft.com/v1.0/me/sendMail",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json=payload,
        timeout=20,
    )
    if resp.status_code >= 400:
        raise SendError(f"Microsoft Graph error {resp.status_code}: {resp.text[:300]}")


def send_email(account, to_email, subject, body, is_html=False):
    if account.provider == account.Provider.GOOGLE:
        return _send_via_gmail(account, to_email, subject, body, is_html)
    if account.provider == account.Provider.MICROSOFT:
        return _send_via_microsoft(account, to_email, subject, body, is_html)
    raise SendError(f"Unsupported provider: {account.provider}")
