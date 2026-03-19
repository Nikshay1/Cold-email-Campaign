"""Inbox management router."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models import Inbox, InboxHealth

router = APIRouter()


class InboxCreate(BaseModel):
    email: str
    display_name: str
    domain: str
    daily_limit: int = 40


class InboxResponse(BaseModel):
    id: str
    email: str
    display_name: str
    domain: str
    daily_limit: int
    health: str
    is_warmup_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/", response_model=InboxResponse, status_code=201)
async def create_inbox(data: InboxCreate, db: AsyncSession = Depends(get_db)):
    inbox = Inbox(**data.model_dump())
    db.add(inbox)
    await db.flush()
    return inbox


@router.get("/", response_model=list[InboxResponse])
async def list_inboxes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Inbox).order_by(Inbox.domain))
    return result.scalars().all()


@router.patch("/{inbox_id}/health")
async def update_inbox_health(
    inbox_id: str,
    health: InboxHealth,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Inbox).where(Inbox.id == inbox_id))
    inbox = result.scalar_one_or_none()
    if not inbox:
        raise HTTPException(status_code=404, detail="Inbox not found")
    inbox.health = health
    return {"message": f"Inbox health set to {health}"}


@router.delete("/{inbox_id}")
async def delete_inbox(inbox_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Inbox).where(Inbox.id == inbox_id))
    inbox = result.scalar_one_or_none()
    if not inbox:
        raise HTTPException(status_code=404, detail="Inbox not found")
    await db.delete(inbox)
    await db.commit()
    return {"message": "Inbox deleted"}
