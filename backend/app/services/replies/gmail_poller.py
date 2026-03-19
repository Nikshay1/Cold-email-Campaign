"""Gmail inbox poller: detects replies to campaign emails every 5 min."""

import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models import EmailRecord, EmailStatus, Inbox, InboxHealth, Reply, ReplyClassification, Lead, Campaign
from app.services.replies.classifier import classify_reply
from app.services.replies.notifier import notify_founder

settings = get_settings()
logger = logging.getLogger(__name__)


async def poll_replies_task(ctx: dict):
    """arq cron task: poll all healthy inboxes for replies."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Inbox).where(Inbox.health == InboxHealth.GOOD)
        )
        inboxes = result.scalars().all()

        logger.info(f"Polling {len(inboxes)} inboxes for replies...")
        for inbox in inboxes:
            try:
                await _poll_inbox(inbox, db)
            except Exception as e:
                logger.error(f"Error polling inbox {inbox.email}: {e}")
        await db.commit()


async def _poll_inbox(inbox: Inbox, db: AsyncSession):
    """Poll a single inbox for new replies to campaign emails."""
    if settings.mock_mode or not inbox.gmail_access_token:
        logger.debug(f"[MOCK] Skipping reply poll for {inbox.email}")
        return

    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        creds = Credentials(
            token=inbox.gmail_access_token,
            refresh_token=inbox.gmail_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        service = build("gmail", "v1", credentials=creds, cache_discovery=False)

        # Fetch unread messages that are replies (have In-Reply-To header)
        msgs_result = service.users().messages().list(
            userId="me",
            q="is:unread label:inbox -from:me",
            maxResults=50,
        ).execute()

        messages = msgs_result.get("messages", [])
        for msg_meta in messages:
            msg = service.users().messages().get(
                userId="me",
                id=msg_meta["id"],
                format="full",
            ).execute()
            await _process_message(msg, inbox, db, service)

    except Exception as e:
        logger.error(f"Gmail API error for {inbox.email}: {e}")


async def _process_message(msg: dict, inbox: Inbox, db: AsyncSession, service):
    """Check if a message is a reply to one of our campaigns and process it."""
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    thread_id = msg.get("threadId")
    in_reply_to = headers.get("in-reply-to", "")
    from_email = headers.get("from", "")

    if not in_reply_to and not thread_id:
        return

    # Find the original email record by Gmail thread ID
    result = await db.execute(
        select(EmailRecord).where(
            EmailRecord.gmail_thread_id == thread_id,
            EmailRecord.status == EmailStatus.SENT,
        )
    )
    email_record = result.scalar_one_or_none()

    if not email_record:
        return

    # Don't process if reply already exists
    existing_reply = await db.execute(
        select(Reply).where(Reply.email_record_id == email_record.id)
    )
    if existing_reply.scalar_one_or_none():
        return

    # Extract reply text
    reply_text = _extract_text(msg)
    if not reply_text:
        return

    logger.info(f"🔔 Reply detected from {from_email} on thread {thread_id}")

    # Classify with Claude
    classification_result = await classify_reply(reply_text)

    # Pause sequence for this lead
    await _pause_lead_sequence(email_record.lead_id, db)

    # Save reply to DB
    reply = Reply(
        email_record_id=email_record.id,
        raw_text=reply_text[:10000],
        classification=classification_result["classification"],
        confidence=classification_result["confidence"],
        ai_summary=classification_result["summary"],
        suggested_talking_points=classification_result.get("talking_points", []),
        needs_human_reply=True,
        received_at=datetime.utcnow(),
    )
    db.add(reply)
    await db.flush()

    # Get lead info for notification
    lead_result = await db.execute(select(Lead).where(Lead.id == email_record.lead_id))
    lead = lead_result.scalar_one()

    # Notify Nikshay — always, for every reply
    await notify_founder(lead=lead, reply=reply, email_record=email_record)

    # Mark message as read in Gmail
    try:
        service.users().messages().modify(
            userId="me",
            id=msg["id"],
            body={"removeLabelIds": ["UNREAD"]},
        ).execute()
    except Exception:
        pass


async def _pause_lead_sequence(lead_id: str, db: AsyncSession):
    """Pause all queued emails for a lead."""
    result = await db.execute(
        select(EmailRecord).where(
            EmailRecord.lead_id == lead_id,
            EmailRecord.status == EmailStatus.QUEUED,
        )
    )
    queued = result.scalars().all()
    for record in queued:
        record.status = EmailStatus.FAILED  # Will be labelled as "paused" in UI
    logger.info(f"Paused {len(queued)} queued emails for lead {lead_id}")


def _extract_text(msg: dict) -> str:
    """Extract plain text from a Gmail message."""
    import base64

    payload = msg.get("payload", {})
    parts = payload.get("parts", [payload])

    for part in parts:
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    return ""
