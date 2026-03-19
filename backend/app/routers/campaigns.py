"""Campaigns router: CRUD + sequence launcher."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
import arq

from app.database import get_db
from app.models import Campaign, CampaignStatus, Lead, LeadTier, EmailRecord, EmailStatus
from app.config import get_settings
from app.services.ai.personalizer import personalize_email
from app.services.sending.scheduler import get_randomized_send_time

settings = get_settings()
router = APIRouter()
logger = logging.getLogger(__name__)

SEQUENCE_STEPS = {
    "tier1": [0, 3, 7, 14, 21],   # days after initial send
    "tier2": [0, 4, 10],
    "tier3": [0, 5],
}


class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sequence_type: str = "tier1"
    is_vc_campaign: bool = False
    value_proposition: str
    pain_point: str
    lead_ids: Optional[list[str]] = None  # specific leads; if None, auto-select by tier


class CampaignResponse(BaseModel):
    id: str
    name: str
    status: str
    sequence_type: str
    is_vc_campaign: bool
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
    campaign = Campaign(
        name=data.name,
        description=data.description,
        sequence_type=data.sequence_type,
        is_vc_campaign=data.is_vc_campaign,
        value_proposition=data.value_proposition,
        pain_point=data.pain_point,
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
    """Launch campaign: generates emails + enqueues send jobs."""
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status == CampaignStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Campaign already active")

    # Select leads for campaign
    tier_map = {"tier1": LeadTier.TIER1, "tier2": LeadTier.TIER2, "tier3": LeadTier.TIER3}
    tier = tier_map.get(campaign.sequence_type, LeadTier.TIER2)
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

    steps = SEQUENCE_STEPS.get(campaign.sequence_type, SEQUENCE_STEPS["tier2"])
    records_created = 0

    for lead in leads:
        email_result = await personalize_email(
            lead=lead,
            campaign_id=campaign.id,
            value_proposition=campaign.value_proposition,
            pain_point=campaign.pain_point,
            sequence_step=1,
        )

        for step_num, day_offset in enumerate(steps, start=1):
            jitter_add = step_num * 3600  # spread steps across hours
            send_time = get_randomized_send_time(jitter_add_seconds=day_offset * 86400 + jitter_add)

            subject = email_result.subject
            if step_num > 1:
                subject = f"Re: {email_result.subject}"

            record = EmailRecord(
                lead_id=lead.id,
                campaign_id=campaign.id,
                subject=subject,
                body=email_result.body,
                personalization_score=email_result.personalization_score,
                sequence_step=step_num,
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
        "message": f"Campaign launched with {len(leads)} leads, {records_created} emails queued",
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
    result = await db.execute(select(Campaign).order_by(Campaign.created_at.desc()))
    return result.scalars().all()


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
