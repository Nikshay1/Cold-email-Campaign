"""Campaigns router: CRUD + launch (Templated)."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import arq
import io
import csv

from app.database import get_db
from app.models import Campaign, CampaignStatus, Lead, EmailRecord, EmailStatus, Inbox
from app.config import get_settings
from app.services.templating import render_template
from app.services.sending.scheduler import get_randomized_send_time

settings = get_settings()
router = APIRouter()
logger = logging.getLogger(__name__)

def get_next_business_day(current_date):
    next_day = current_date + timedelta(days=1)
    while next_day.weekday() >= 5:
        next_day += timedelta(days=1)
    return next_day

class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    subject: str
    body_template: str
    selected_inbox_ids: list[str]


class CampaignResponse(BaseModel):
    id: str
    name: str
    status: str
    total_leads: int
    sent_count: int
    open_count: int
    reply_count: int
    bounce_count: int
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/", response_model=CampaignResponse, status_code=201)
async def create_campaign(data: CampaignCreate, db: AsyncSession = Depends(get_db)):
    if not data.selected_inbox_ids:
        raise HTTPException(status_code=400, detail="Must select at least one inbox")
        
    campaign = Campaign(
        name=data.name,
        description=data.description,
        subject=data.subject,
        body_template=data.body_template,
        selected_inboxes=data.selected_inbox_ids,
    )
    db.add(campaign)
    await db.flush()
    return campaign


@router.post("/{campaign_id}/launch")
async def launch_campaign(
    campaign_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Launch campaign: generates templated emails + enqueues send jobs via round robin."""
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status == CampaignStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Campaign already active")

    # Fetch selected inboxes
    inboxes_result = await db.execute(
        select(Inbox).where(Inbox.id.in_(campaign.selected_inboxes or []))
    )
    inboxes = inboxes_result.scalars().all()
    if not inboxes:
        raise HTTPException(status_code=400, detail="Selected inboxes not found in database; cannot launch.")

    # Select leads for campaign
    leads_result = await db.execute(
        select(Lead).where(
            Lead.is_suppressed == False,
            Lead.status == "new",
        ).order_by(Lead.icp_score.desc())
    )
    leads = leads_result.scalars().all()

    if not leads:
        raise HTTPException(status_code=400, detail="No eligible leads found")

    campaign.status = CampaignStatus.ACTIVE
    campaign.total_leads = len(leads)

    records_created = 0

    # Round-robin distribution
    inbox_states = {inb.id: {"date": datetime.utcnow().date(), "count": 0} for inb in inboxes}

    for i, lead in enumerate(leads):
        assigned_inbox = inboxes[i % len(inboxes)]
        state = inbox_states[assigned_inbox.id]
        
        # Enforce daily limit specific to inbox
        if state["count"] >= assigned_inbox.daily_limit:
            state["date"] = get_next_business_day(state["date"])
            state["count"] = 0
            
        # Space out emails by 5 mins per lead 
        jitter_add = state["count"] * 60 * 5 
        send_time = get_randomized_send_time(
            jitter_add_seconds=jitter_add, 
            target_date=state["date"]
        )
        state["count"] += 1

        # Template substitution
        subject = render_template(campaign.subject, lead)
        body = render_template(campaign.body_template, lead)

        record = EmailRecord(
            lead_id=lead.id,
            campaign_id=campaign.id,
            inbox_id=assigned_inbox.id, # Explicit round-robin assignment
            subject=subject,
            body=body,
            sequence_step=1,
            status=EmailStatus.QUEUED,
            scheduled_at=send_time,
        )
        db.add(record)
        await db.flush()
        records_created += 1

        # Enqueue arq deferred job
        background_tasks.add_task(_enqueue_send_job, record.id, send_time)

    await db.commit()
    return {
        "message": f"Campaign launched with {len(leads)} leads equally divided across {len(inboxes)} sender inboxes.",
        "campaign_id": campaign_id,
        "emails_queued": records_created,
    }


async def _enqueue_send_job(record_id: str, send_time: datetime):
    """Enqueue arq job with a deferred execution time."""
    try:
        redis = arq.create_pool(arq.connections.RedisSettings.from_dsn(settings.redis_url))
        pool = await redis
        defer_by = (send_time - datetime.utcnow()).total_seconds()
        if defer_by < 0:
            defer_by = 60
        await pool.enqueue_job("send_email_task", record_id, _defer_by=int(defer_by))
        await pool.aclose()
    except Exception as e:
        logger.error(f"Failed to enqueue job for {record_id}: {e}")


@router.get("/", response_model=list[CampaignResponse])
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    result = await db.execute(select(Campaign).order_by(Campaign.created_at.desc()))
    campaigns = result.scalars().all()
    
    response = []
    for c in campaigns:
        # Dynamically calculate exact counts straight from the EmailRecords
        total = (await db.execute(select(func.count(EmailRecord.id)).where(EmailRecord.campaign_id == c.id))).scalar()
        sent = (await db.execute(select(func.count(EmailRecord.id)).where(EmailRecord.campaign_id == c.id, EmailRecord.status == EmailStatus.SENT))).scalar()
        
        from app.models import Reply
        replies = (await db.execute(
            select(func.count(Reply.id)).join(EmailRecord).where(EmailRecord.campaign_id == c.id)
        )).scalar()
        
        response.append({
            "id": c.id,
            "name": c.name,
            "status": c.status.value,
            "total_leads": total or 0,
            "sent_count": sent or 0,
            "open_count": c.open_count,
            "reply_count": replies or 0,
            "bounce_count": c.bounce_count,
            "created_at": c.created_at
        })
    return response


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.patch("/{campaign_id}/pause")
async def pause_campaign(campaign_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign.status = CampaignStatus.PAUSED
    return {"message": "Campaign paused"}


@router.get("/follow-up-csv")
async def generate_follow_up_csv(db: AsyncSession = Depends(get_db)):
    """Generate and download a CSV of leads that haven't replied in 3 days."""
    from sqlalchemy.orm import selectinload
    
    three_days_ago = datetime.utcnow() - timedelta(days=3)
    
    query = select(EmailRecord).where(
        EmailRecord.status == EmailStatus.SENT,
        EmailRecord.sent_at <= three_days_ago
    ).options(selectinload(EmailRecord.reply), selectinload(EmailRecord.lead))
    
    result = await db.execute(query)
    records = result.scalars().all()
    
    follow_ups = [r for r in records if r.reply is None]
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["email", "first_name", "last_name", "sent_at", "subject"])
    
    for r in follow_ups:
        writer.writerow([
            r.lead.email,
            r.lead.first_name,
            r.lead.last_name or "",
            r.sent_at.isoformat() if r.sent_at else "",
            r.subject
        ])
        
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=follow_up.csv"}
    )

