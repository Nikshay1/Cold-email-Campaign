"""Founder notification system: Slack + email alerts for VC replies."""

import json
import logging
import httpx
from datetime import datetime

from app.config import get_settings
from app.models import Lead, Reply, EmailRecord, ReplyClassification

settings = get_settings()
logger = logging.getLogger(__name__)

CLASSIFICATION_EMOJI = {
    "INTERESTED": "🔥",
    "NOT_NOW": "🟡",
    "WRONG_PERSON": "🔀",
    "UNSUBSCRIBE": "🚫",
    "OTHER": "💬",
}


async def notify_founder(lead: Lead, reply: Reply, email_record: EmailRecord):
    """Send Slack + email notification to Nikshay for every reply."""
    await _notify_slack(lead, reply, email_record)
    await _notify_email(lead, reply)


async def _notify_slack(lead: Lead, reply: Reply, email_record: EmailRecord):
    """Send rich Slack block message."""
    if not settings.slack_webhook_url or settings.mock_mode:
        logger.info(f"[MOCK] Slack notify: {reply.classification} from {lead.email}")
        return

    emoji = CLASSIFICATION_EMOJI.get(reply.classification, "📩")
    talking_points_text = "\n".join(
        f"• {pt}" for pt in (reply.suggested_talking_points or [])
    ) or "_No specific talking points_"

    gmail_link = (
        f"https://mail.google.com/mail/u/0/#inbox/{email_record.gmail_thread_id}"
        if email_record.gmail_thread_id
        else "#"
    )

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{emoji} VC Reply — {reply.classification}"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Name:*\n{lead.first_name} {lead.last_name or ''}"},
                {"type": "mrkdwn", "text": f"*Title:*\n{lead.title or 'N/A'}"},
                {"type": "mrkdwn", "text": f"*Company:*\n{lead.company_name or 'N/A'} ({lead.company_funding_stage or 'N/A'})"},
                {"type": "mrkdwn", "text": f"*Email:*\n{lead.email}"},
            ],
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Their reply:*\n```{reply.raw_text[:800]}```",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*AI Summary:* {reply.ai_summary}\n\n*Talking points for your reply:*\n{talking_points_text}",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Open in Gmail"},
                    "url": gmail_link,
                    "style": "primary",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View in Dashboard"},
                    "url": "http://localhost:3000/replies",
                },
            ],
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"⏱ Reply received at {reply.received_at.strftime('%d %b %Y, %H:%M UTC')} | Sequence auto-paused"}
            ],
        },
    ]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                settings.slack_webhook_url,
                json={"blocks": blocks, "channel": settings.slack_channel},
            )
            resp.raise_for_status()
            reply.slack_notified = True
            logger.info(f"Slack notified for reply from {lead.email}")
    except Exception as e:
        logger.error(f"Slack notification failed: {e}")


async def _notify_email(lead: Lead, reply: Reply):
    """Send email notification to founder (via SendGrid if configured)."""
    if not settings.sendgrid_api_key or settings.mock_mode:
        logger.info(f"[MOCK] Email notify to {settings.founder_email}: reply from {lead.email}")
        reply.email_notified = True
        return

    try:
        import httpx
        emoji = CLASSIFICATION_EMOJI.get(reply.classification, "📩")
        subject = f"{emoji} VC Reply [{reply.classification}]: {lead.first_name} from {lead.company_name or 'Unknown'}"
        body = f"""Hi Nikshay,

You got a reply from a VC!

Name: {lead.first_name} {lead.last_name or ''}
Title: {lead.title or 'N/A'}
Company: {lead.company_name or 'N/A'} ({lead.company_funding_stage or 'N/A'})
Email: {lead.email}

Classification: {reply.classification} (confidence: {reply.confidence:.0%})
Summary: {reply.ai_summary}

Talking points:
{chr(10).join(f'• {pt}' for pt in (reply.suggested_talking_points or [])) or 'N/A'}

Their reply:
-----------
{reply.raw_text[:2000]}
-----------

⚠ The automated sequence for this lead has been PAUSED.
Reply to them personally from your inbox.

— Cortexa System
"""

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {settings.sendgrid_api_key}"},
                json={
                    "personalizations": [{"to": [{"email": settings.founder_email}]}],
                    "from": {"email": "system@cortexalabs.io", "name": "Cortexa System"},
                    "subject": subject,
                    "content": [{"type": "text/plain", "value": body}],
                },
            )
            resp.raise_for_status()
            reply.email_notified = True
    except Exception as e:
        logger.error(f"Email notification failed: {e}")
