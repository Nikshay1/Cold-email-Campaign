"""Analytics router: campaign metrics, domain health, reply inbox."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from app.database import get_db
from app.models import (
    Campaign, EmailRecord, EmailStatus, Reply, ReplyClassification,
    Lead, Inbox, InboxHealth
)

router = APIRouter()


@router.get("/campaigns/{campaign_id}")
async def campaign_stats(campaign_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            func.count(EmailRecord.id).label("total"),
            func.sum(case((EmailRecord.status == EmailStatus.SENT, 1), else_=0)).label("sent"),
            func.sum(case((EmailRecord.status == EmailStatus.OPENED, 1), else_=0)).label("opened"),
            func.sum(case((EmailRecord.status == EmailStatus.BOUNCED, 1), else_=0)).label("bounced"),
            func.sum(case((EmailRecord.status == EmailStatus.FAILED, 1), else_=0)).label("failed"),
        ).where(EmailRecord.campaign_id == campaign_id)
    )
    stats = result.one()
    total = stats.total or 1

    reply_result = await db.execute(
        select(func.count(Reply.id)).join(
            EmailRecord, Reply.email_record_id == EmailRecord.id
        ).where(EmailRecord.campaign_id == campaign_id)
    )
    reply_count = reply_result.scalar() or 0

    positive_result = await db.execute(
        select(func.count(Reply.id)).join(
            EmailRecord, Reply.email_record_id == EmailRecord.id
        ).where(
            EmailRecord.campaign_id == campaign_id,
            Reply.classification == ReplyClassification.INTERESTED,
        )
    )
    positive_count = positive_result.scalar() or 0

    sent = stats.sent or 0
    return {
        "campaign_id": campaign_id,
        "total_queued": stats.total,
        "sent": sent,
        "opened": stats.opened,
        "bounced": stats.bounced,
        "replies": reply_count,
        "positive_replies": positive_count,
        "open_rate": round((stats.opened or 0) / max(sent, 1) * 100, 2),
        "reply_rate": round(reply_count / max(sent, 1) * 100, 2),
        "positive_reply_rate": round(positive_count / max(reply_count, 1) * 100, 2),
        "bounce_rate": round((stats.bounced or 0) / max(sent, 1) * 100, 2),
    }


@router.get("/domains")
async def domain_health(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Inbox).order_by(Inbox.domain))
    inboxes = result.scalars().all()

    domains: dict = {}
    for inbox in inboxes:
        if inbox.domain not in domains:
            domains[inbox.domain] = {
                "domain": inbox.domain,
                "inboxes": 0,
                "health": inbox.health,
                "daily_limit_total": 0,
            }
        domains[inbox.domain]["inboxes"] += 1
        domains[inbox.domain]["daily_limit_total"] += inbox.daily_limit
        if inbox.health != InboxHealth.GOOD:
            domains[inbox.domain]["health"] = inbox.health

    return list(domains.values())


@router.get("/replies")
async def reply_inbox(
    handled: bool = False,
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
):
    """Priority reply inbox for the founder."""
    result = await db.execute(
        select(Reply, Lead)
        .join(EmailRecord, Reply.email_record_id == EmailRecord.id)
        .join(Lead, EmailRecord.lead_id == Lead.id)
        .where(Reply.handled_by_human == handled)
        .order_by(
            # INTERESTED first
            case(
                (Reply.classification == ReplyClassification.INTERESTED, 0),
                (Reply.classification == ReplyClassification.NOT_NOW, 1),
                else_=2,
            ),
            Reply.received_at.desc()
        )
        .offset(skip)
        .limit(limit)
    )
    rows = result.all()

    return [
        {
            "reply_id": r.Reply.id,
            "classification": r.Reply.classification,
            "confidence": r.Reply.confidence,
            "ai_summary": r.Reply.ai_summary,
            "talking_points": r.Reply.suggested_talking_points,
            "raw_text_preview": r.Reply.raw_text[:300],
            "needs_human_reply": r.Reply.needs_human_reply,
            "received_at": r.Reply.received_at,
            "lead": {
                "id": r.Lead.id,
                "name": f"{r.Lead.first_name} {r.Lead.last_name or ''}".strip(),
                "email": r.Lead.email,
                "title": r.Lead.title,
                "company": r.Lead.company_name,
                "funding_stage": r.Lead.company_funding_stage,
            },
        }
        for r in rows
    ]


@router.post("/replies/sync")
async def force_sync_replies():
    """Force an immediate sync of Gmail replies bypassing the 5-minute cron."""
    from app.services.replies.gmail_poller import poll_replies_task
    from fastapi import HTTPException
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        await poll_replies_task({})
        return {"message": "Sync complete"}
    except Exception as e:
        logger.error(f"Force sync failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync. Is your App Password valid?")


@router.post("/replies/{reply_id}/handled")
async def mark_reply_handled(reply_id: str, db: AsyncSession = Depends(get_db)):
    """Mark a reply as handled by Nikshay."""
    from datetime import datetime
    result = await db.execute(select(Reply).where(Reply.id == reply_id))
    reply = result.scalar_one_or_none()
    if not reply:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Reply not found")
    reply.handled_by_human = True
    reply.needs_human_reply = False
    reply.handled_at = datetime.utcnow()
    return {"message": "Marked as handled"}


@router.get("/funnel")
async def global_funnel(db: AsyncSession = Depends(get_db)):
    """Aggregate funnel across all campaigns."""
    stats = await db.execute(
        select(
            func.count(EmailRecord.id).label("total"),
            func.sum(case((EmailRecord.status.in_([EmailStatus.SENT, EmailStatus.OPENED]), 1), else_=0)).label("delivered"),
            func.sum(case((EmailRecord.status == EmailStatus.OPENED, 1), else_=0)).label("opened"),
            func.sum(case((EmailRecord.status == EmailStatus.BOUNCED, 1), else_=0)).label("bounced"),
        )
    )
    s = stats.one()

    replies = await db.execute(select(func.count(Reply.id)))
    reply_count = replies.scalar() or 0

    positive = await db.execute(
        select(func.count(Reply.id)).where(Reply.classification == ReplyClassification.INTERESTED)
    )
    pos_count = positive.scalar() or 0

    delivered = s.delivered or 0
    return {
        "sent": s.total,
        "delivered": delivered,
        "opened": s.opened,
        "bounced": s.bounced,
        "replied": reply_count,
        "positive_replies": pos_count,
        "open_rate": round((s.opened or 0) / max(delivered, 1) * 100, 1),
        "reply_rate": round(reply_count / max(delivered, 1) * 100, 1),
        "positive_rate": round(pos_count / max(reply_count, 1) * 100, 1),
        "bounce_rate": round((s.bounced or 0) / max(s.total or 1, 1) * 100, 1),
    }
