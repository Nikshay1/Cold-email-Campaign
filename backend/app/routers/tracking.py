"""Email tracking pixel + unsubscribe handler."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.database import get_db
from app.models import EmailRecord, EmailStatus, Lead

router = APIRouter()

# 1x1 transparent GIF pixel
TRACKING_PIXEL = bytes([
    0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x01, 0x00, 0x01, 0x00,
    0x80, 0x00, 0x00, 0xff, 0xff, 0xff, 0x00, 0x00, 0x00, 0x21,
    0xf9, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x2c, 0x00, 0x00,
    0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0x02, 0x02, 0x44,
    0x01, 0x00, 0x3b,
])


@router.get("/open/{tracking_id}")
async def track_open(tracking_id: str, db: AsyncSession = Depends(get_db)):
    """Tracking pixel endpoint — records email open."""
    result = await db.execute(
        select(EmailRecord).where(EmailRecord.tracking_id == tracking_id)
    )
    record = result.scalar_one_or_none()
    if record and record.status == EmailStatus.SENT:
        record.status = EmailStatus.OPENED
        record.opened_at = datetime.utcnow()
        await db.commit()

    return Response(content=TRACKING_PIXEL, media_type="image/gif")


@router.get("/unsubscribe/{email}")
async def unsubscribe(email: str, db: AsyncSession = Depends(get_db)):
    """One-click unsubscribe handler."""
    result = await db.execute(select(Lead).where(Lead.email == email.lower()))
    lead = result.scalar_one_or_none()
    if lead:
        lead.is_suppressed = True
        lead.suppression_reason = "unsubscribe"
        lead.status = "unsubscribed"
        await db.commit()

    return {"message": "You have been unsubscribed. You won't hear from us again."}
