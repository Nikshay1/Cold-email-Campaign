"""SQLAlchemy ORM models for Cortexa Labs cold email system."""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer,
    String, Text, Enum, JSON, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class LeadTier(str, PyEnum):
    TIER1 = "tier1"
    TIER2 = "tier2"
    TIER3 = "tier3"


class LeadStatus(str, PyEnum):
    NEW = "new"
    ENRICHED = "enriched"
    QUEUED = "queued"
    ACTIVE = "active"
    REPLIED = "replied"
    UNSUBSCRIBED = "unsubscribed"
    BOUNCED = "bounced"


class CampaignStatus(str, PyEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class InboxHealth(str, PyEnum):
    GOOD = "good"
    WARMING = "warming"
    PAUSED = "paused"
    SUSPENDED = "suspended"


class EmailStatus(str, PyEnum):
    QUEUED = "queued"
    SENT = "sent"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    FAILED = "failed"


class ReplyClassification(str, PyEnum):
    INTERESTED = "INTERESTED"
    NOT_NOW = "NOT_NOW"
    WRONG_PERSON = "WRONG_PERSON"
    UNSUBSCRIBE = "UNSUBSCRIBE"
    OTHER = "OTHER"


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    title: Mapped[Optional[str]] = mapped_column(String(200))
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Company
    company_name: Mapped[Optional[str]] = mapped_column(String(200))
    company_domain: Mapped[Optional[str]] = mapped_column(String(200))
    company_industry: Mapped[Optional[str]] = mapped_column(String(200))
    company_size: Mapped[Optional[str]] = mapped_column(String(50))
    company_funding_stage: Mapped[Optional[str]] = mapped_column(String(50))
    company_website_summary: Mapped[Optional[str]] = mapped_column(Text)
    company_recent_news: Mapped[Optional[str]] = mapped_column(Text)
    tech_stack: Mapped[Optional[list]] = mapped_column(JSON)
    pain_points: Mapped[Optional[list]] = mapped_column(JSON)

    # LinkedIn
    linkedin_recent_post: Mapped[Optional[str]] = mapped_column(Text)
    linkedin_post_topic: Mapped[Optional[str]] = mapped_column(String(200))

    # Scoring
    icp_score: Mapped[int] = mapped_column(Integer, default=0)
    tier: Mapped[LeadTier] = mapped_column(Enum(LeadTier), default=LeadTier.TIER3)
    status: Mapped[LeadStatus] = mapped_column(Enum(LeadStatus), default=LeadStatus.NEW)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Suppression
    is_suppressed: Mapped[bool] = mapped_column(Boolean, default=False)
    suppression_reason: Mapped[Optional[str]] = mapped_column(String(50))

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    emails: Mapped[list["EmailRecord"]] = relationship("EmailRecord", back_populates="lead")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[CampaignStatus] = mapped_column(Enum(CampaignStatus), default=CampaignStatus.DRAFT)
    sequence_type: Mapped[str] = mapped_column(String(10), default="tier1")  # tier1, tier2, tier3

    # VC mode: no auto-replies, human handles everything
    is_vc_campaign: Mapped[bool] = mapped_column(Boolean, default=False)

    # Sending config
    sending_domains: Mapped[Optional[list]] = mapped_column(JSON)  # list of domain strings
    
    # Template config
    subject: Mapped[str] = mapped_column(String(200))
    body_template: Mapped[str] = mapped_column(Text)
    selected_inboxes: Mapped[Optional[list]] = mapped_column(JSON) # list of Inbox IDs to rotate between
    
    total_leads: Mapped[int] = mapped_column(Integer, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    open_count: Mapped[int] = mapped_column(Integer, default=0)
    reply_count: Mapped[int] = mapped_column(Integer, default=0)
    bounce_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    emails: Mapped[list["EmailRecord"]] = relationship("EmailRecord", back_populates="campaign")


class Inbox(Base):
    __tablename__ = "inboxes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    domain: Mapped[str] = mapped_column(String(200), nullable=False)
    daily_limit: Mapped[int] = mapped_column(Integer, default=40)
    health: Mapped[InboxHealth] = mapped_column(Enum(InboxHealth), default=InboxHealth.WARMING)

    # Gmail OAuth tokens (stored encrypted in production)
    gmail_access_token: Mapped[Optional[str]] = mapped_column(Text)
    gmail_refresh_token: Mapped[Optional[str]] = mapped_column(Text)
    gmail_token_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime)

    is_warmup_active: Mapped[bool] = mapped_column(Boolean, default=True)
    warmup_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    emails: Mapped[list["EmailRecord"]] = relationship("EmailRecord", back_populates="inbox")


class EmailRecord(Base):
    __tablename__ = "email_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    lead_id: Mapped[str] = mapped_column(String(36), ForeignKey("leads.id"), nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("campaigns.id"), nullable=False)
    inbox_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("inboxes.id"))

    subject: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    sequence_step: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[EmailStatus] = mapped_column(
        Enum(EmailStatus), default=EmailStatus.QUEUED
    ) # Gmail threading
    gmail_message_id: Mapped[Optional[str]] = mapped_column(String(200))
    gmail_thread_id: Mapped[Optional[str]] = mapped_column(String(200))

    # Tracking
    tracking_id: Mapped[str] = mapped_column(String(36), default=gen_uuid, unique=True)
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    clicked_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    bounced_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    bounce_type: Mapped[Optional[str]] = mapped_column(String(50))

    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    lead: Mapped["Lead"] = relationship("Lead", back_populates="emails")
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="emails")
    inbox: Mapped[Optional["Inbox"]] = relationship("Inbox", back_populates="emails")
    reply: Mapped[Optional["Reply"]] = relationship("Reply", back_populates="email_record", uselist=False)


class Reply(Base):
    __tablename__ = "replies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    email_record_id: Mapped[str] = mapped_column(String(36), ForeignKey("email_records.id"), nullable=False, unique=True)

    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    classification: Mapped[ReplyClassification] = mapped_column(Enum(ReplyClassification))
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text)
    suggested_talking_points: Mapped[Optional[list]] = mapped_column(JSON)

    # Human handling state
    needs_human_reply: Mapped[bool] = mapped_column(Boolean, default=True)
    handled_by_human: Mapped[bool] = mapped_column(Boolean, default=False)
    handled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Notifications sent
    slack_notified: Mapped[bool] = mapped_column(Boolean, default=False)
    email_notified: Mapped[bool] = mapped_column(Boolean, default=False)

    received_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    email_record: Mapped["EmailRecord"] = relationship("EmailRecord", back_populates="reply")


class AppConfig(Base):
    """Singleton table for dynamic UI system settings."""
    __tablename__ = "app_config"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: "singleton")
    groq_api_key: Mapped[Optional[str]] = mapped_column(String(500))
    groq_model: Mapped[str] = mapped_column(String(100), default="llama-3.3-70b-versatile")

    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
