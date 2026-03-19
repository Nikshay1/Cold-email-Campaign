"""Lead ingestion: CSV upload, JSON API, validation, deduplication."""

import csv
import io
import hashlib
import re
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.database import get_db
from app.models import Lead, LeadStatus
from app.services.leads.scoring import score_lead
from app.services.leads.enrichment import enrich_lead

router = APIRouter()

DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "tempmail.com", "10minutemail.com",
    "throwaway.email", "yopmail.com", "sharklasers.com", "guerrillamailblock.com",
}

ROLE_PREFIXES = {
    "noreply", "no-reply", "unsubscribe", "postmaster", "abuse",
    "support", "info", "hello", "admin", "billing",
}

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LeadCreate(BaseModel):
    email: str
    first_name: str
    last_name: Optional[str] = None
    title: Optional[str] = None
    company_name: Optional[str] = None
    company_domain: Optional[str] = None
    linkedin_url: Optional[str] = None
    company_funding_stage: Optional[str] = None
    company_size: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v):
            raise ValueError("Invalid email format")
        domain = v.split("@")[1]
        if domain in DISPOSABLE_DOMAINS:
            raise ValueError("Disposable email not allowed")
        prefix = v.split("@")[0]
        if any(prefix.startswith(r) for r in ROLE_PREFIXES):
            raise ValueError("Role-based email not allowed")
        return v


class LeadResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: Optional[str]
    title: Optional[str]
    company_name: Optional[str]
    icp_score: int
    tier: str
    status: str

    class Config:
        from_attributes = True


def _email_hash(email: str) -> str:
    return hashlib.sha256(email.lower().encode()).hexdigest()


async def _upsert_lead(data: LeadCreate, db: AsyncSession) -> tuple[Lead, bool]:
    """Insert lead or skip if duplicate. Returns (lead, is_new)."""
    existing = await db.execute(select(Lead).where(Lead.email == data.email))
    existing_lead = existing.scalar_one_or_none()
    if existing_lead:
        return existing_lead, False

    lead = Lead(**data.model_dump(exclude_none=True))
    # Score and tier
    score = score_lead(lead)
    lead.icp_score = score
    from app.services.leads.scoring import assign_tier
    lead.tier = assign_tier(score)
    db.add(lead)
    return lead, True


@router.post("/", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(data: LeadCreate, db: AsyncSession = Depends(get_db)):
    lead, is_new = await _upsert_lead(data, db)
    if not is_new:
        raise HTTPException(status_code=409, detail="Lead already exists")
    await db.flush()
    return lead


@router.post("/upload", status_code=status.HTTP_200_OK)
async def upload_leads_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Bulk upload leads from CSV file."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files accepted")

    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))

    results = {"imported": 0, "skipped": 0, "errors": []}

    for i, row in enumerate(reader):
        try:
            # Normalize column names
            normalized = {k.lower().strip().replace(" ", "_"): v.strip() for k, v in row.items()}
            email = normalized.get("email", "")
            if not email:
                results["errors"].append(f"Row {i+2}: missing email")
                continue

            data = LeadCreate(
                email=email,
                first_name=normalized.get("first_name", "").strip() or email.split("@")[0],
                last_name=normalized.get("last_name"),
                title=normalized.get("title") or normalized.get("job_title"),
                company_name=normalized.get("company_name") or normalized.get("company"),
                company_domain=normalized.get("company_domain") or normalized.get("domain"),
                company_funding_stage=normalized.get("funding_stage") or normalized.get("company_funding_stage"),
                company_size=normalized.get("company_size") or normalized.get("employees"),
                linkedin_url=normalized.get("linkedin_url") or normalized.get("linkedin"),
            )
            _, is_new = await _upsert_lead(data, db)
            if is_new:
                results["imported"] += 1
            else:
                results["skipped"] += 1
        except Exception as e:
            results["errors"].append(f"Row {i+2}: {str(e)}")

    await db.flush()
    return results


@router.get("/", response_model=list[LeadResponse])
async def list_leads(
    skip: int = 0,
    limit: int = 50,
    tier: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Lead).where(Lead.is_suppressed == False)
    if tier:
        query = query.where(Lead.tier == tier)
    query = query.order_by(Lead.icp_score.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead
