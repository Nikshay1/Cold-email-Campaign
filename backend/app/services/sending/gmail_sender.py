"""Gmail API email sender using OAuth2."""

import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from app.config import get_settings
from app.models import Inbox

settings = get_settings()
logger = logging.getLogger(__name__)


def _build_gmail_service(inbox: Inbox):
    """Build an authenticated Gmail API service for an inbox."""
    creds = Credentials(
        token=inbox.gmail_access_token,
        refresh_token=inbox.gmail_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _build_message(
    sender_name: str,
    from_email: str,
    to_email: str,
    subject: str,
    body: str,
    tracking_pixel_url: Optional[str] = None,
    unsubscribe_url: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> dict:
    """Build a properly formatted email message."""
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{sender_name} <{from_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject

    if reply_to:
        msg["Reply-To"] = reply_to

    # Plain text body (primary)
    full_body = body
    msg.attach(MIMEText(full_body, "plain"))

    # Minimal HTML version with tracking pixel
    html_body = full_body.replace("\n", "<br>")
    if tracking_pixel_url:
        html_body += f'<img src="{tracking_pixel_url}" width="1" height="1" style="display:none" alt="">'
    msg.attach(MIMEText(f"<html><body>{html_body}</body></html>", "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {"raw": raw}


async def send_email_via_gmail(
    inbox: Inbox,
    to_email: str,
    subject: str,
    body: str,
    tracking_pixel_url: Optional[str] = None,
    unsubscribe_url: Optional[str] = None,
) -> dict:
    """Send email via Gmail API. Returns Gmail message metadata."""
    if not inbox.gmail_access_token:
        logger.info(f"[MOCK] Would send from {inbox.email} to {to_email}: {subject}")
        return {
            "id": f"mock_msg_{to_email}_{datetime.utcnow().timestamp()}",
            "threadId": f"mock_thread_{to_email}",
            "mock": True,
        }

    try:
        service = _build_gmail_service(inbox)
        message = _build_message(
            sender_name=inbox.display_name,
            from_email=inbox.email,
            to_email=to_email,
            subject=subject,
            body=body,
            tracking_pixel_url=tracking_pixel_url,
            unsubscribe_url=unsubscribe_url,
        )
        result = service.users().messages().send(userId="me", body=message).execute()
        logger.info(f"Sent email from {inbox.email} to {to_email} — msg_id: {result['id']}")
        return result
    except Exception as e:
        logger.error(f"Gmail send failed from {inbox.email} to {to_email}: {e}")
        raise
