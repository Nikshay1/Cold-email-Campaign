"""arq background task: send a single email."""

import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis

from app.config import get_settings
from app.database import AsyncSessionLocal, get_redis
from app.models import EmailRecord, EmailStatus, Lead, Inbox, Campaign
from app.services.sending.gmail_sender import send_email_via_gmail
from app.services.sending.inbox_rotator import (
    get_next_available_inbox, increment_send_count, NoInboxAvailableError
)

settings = get_settings()
logger = logging.getLogger(__name__)


async def send_email_task(ctx: dict, email_record_id: str):
    """arq task: send a queued EmailRecord. Retries up to 3 times."""
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(EmailRecord)
                .where(EmailRecord.id == email_record_id)
                .join(Lead, EmailRecord.lead_id == Lead.id)
                .join(Campaign, EmailRecord.campaign_id == Campaign.id)
            )
            record = result.scalar_one_or_none()
            if not record:
                logger.error(f"EmailRecord {email_record_id} not found")
                return

            if record.status not in (EmailStatus.QUEUED,):
                logger.info(f"EmailRecord {email_record_id} already in status {record.status}, skipping")
                return

            lead_result = await db.execute(select(Lead).where(Lead.id == record.lead_id))
            lead = lead_result.scalar_one()

            # Skip suppressed leads
            if lead.is_suppressed:
                record.status = EmailStatus.FAILED
                await db.commit()
                return

            redis: aioredis.Redis = await get_redis()

            # Get next available inbox
            try:
                inbox = await get_next_available_inbox(db, redis)
            except NoInboxAvailableError as e:
                logger.warning(f"No inbox available for {email_record_id}: {e}")
                # Re-queue for later — arq will retry
                raise

            # Build URLs
            tracking_url = f"{settings.unsubscribe_base_url.replace('/unsubscribe', '')}/track/open/{record.tracking_id}"
            unsubscribe_url = f"{settings.unsubscribe_base_url}/{lead.email}"

            # Send
            gmail_result = await send_email_via_gmail(
                inbox=inbox,
                to_email=lead.email,
                subject=record.subject,
                body=record.body,
                tracking_pixel_url=tracking_url,
                unsubscribe_url=unsubscribe_url,
            )

            # Update record
            record.status = EmailStatus.SENT
            record.inbox_id = inbox.id
            record.gmail_message_id = gmail_result.get("id")
            record.gmail_thread_id = gmail_result.get("threadId")
            record.sent_at = datetime.utcnow()

            # Increment rate limiter
            await increment_send_count(inbox.email, redis)

            await db.commit()
            logger.info(f"✅ Sent email {email_record_id} to {lead.email}")

        except NoInboxAvailableError:
            raise  # Let arq retry
        except Exception as e:
            logger.error(f"Failed to send {email_record_id}: {e}")
            async with AsyncSessionLocal() as db2:
                result2 = await db2.execute(select(EmailRecord).where(EmailRecord.id == email_record_id))
                rec2 = result2.scalar_one_or_none()
                if rec2:
                    rec2.status = EmailStatus.FAILED
                    await db2.commit()
            raise
