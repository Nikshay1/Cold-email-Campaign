"""Inbox rotation: weighted round-robin with daily limit checking."""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import redis.asyncio as aioredis
from datetime import date

from app.config import get_settings
from app.models import Inbox, InboxHealth, EmailRecord, EmailStatus

settings = get_settings()
logger = logging.getLogger(__name__)


class NoInboxAvailableError(Exception):
    pass


async def get_daily_send_count(inbox_email: str, redis: aioredis.Redis) -> int:
    key = f"sends:{inbox_email}:{date.today().isoformat()}"
    val = await redis.get(key)
    return int(val) if val else 0


async def increment_send_count(inbox_email: str, redis: aioredis.Redis) -> int:
    key = f"sends:{inbox_email}:{date.today().isoformat()}"
    count = await redis.incr(key)
    # Expire at midnight (86400 seconds)
    await redis.expire(key, 86400)
    return count


async def get_next_available_inbox(
    db: AsyncSession,
    redis: aioredis.Redis,
    domain: str | None = None,
) -> Inbox:
    """
    Returns next available inbox via weighted round-robin.
    Skips inboxes that are at their daily cold-email limit or unhealthy.
    """
    query = select(Inbox).where(Inbox.health == InboxHealth.GOOD)
    if domain:
        query = query.where(Inbox.domain == domain)
    query = query.order_by(Inbox.id)

    result = await db.execute(query)
    inboxes = result.scalars().all()

    if not inboxes:
        raise NoInboxAvailableError("No healthy inboxes configured")

    for inbox in inboxes:
        sent_today = await get_daily_send_count(inbox.email, redis)
        cold_limit = int(inbox.daily_limit * (1 - settings.warmup_ratio))
        if sent_today < cold_limit:
            return inbox

    raise NoInboxAvailableError(
        f"All {len(inboxes)} inboxes at daily cold-email limit"
    )
