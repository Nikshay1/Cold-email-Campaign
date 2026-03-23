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

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LeadCreate(BaseModel):
    email: str
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    company_name: Optional[str] = None
    company_domain: Optional[str] = None
    linkedin_url: Optional[str] = None
    company_funding_stage: Optional[str] = None
    company_size: Optional[str] = None
    location: Optional[str] = None
    phone_number: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        # If cell contains multiple emails, take the first valid one
        candidates = [e.strip() for e in re.split(r"[,;\n]", v) if e.strip()]
        for candidate in candidates:
            candidate = candidate.lower()
            if EMAIL_REGEX.match(candidate):
                domain = candidate.split("@")[1]
                if domain not in DISPOSABLE_DOMAINS:
                    return candidate
        raise ValueError(f"No valid email found in: {v[:80]}")


class LeadResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    company_name: Optional[str] = None
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
        if existing_lead.is_suppressed:
            # Resurrect the soft-deleted lead
            existing_lead.is_suppressed = False
            existing_lead.status = LeadStatus.NEW
            
            # Update fields
            for key, value in data.model_dump(exclude_none=True).items():
                setattr(existing_lead, key, value)
                
            # Re-score
            score = score_lead(existing_lead)
            existing_lead.icp_score = score
            from app.services.leads.scoring import assign_tier
            existing_lead.tier = assign_tier(score)
            
            return existing_lead, True
            
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
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            decoded = content.decode("windows-1252")
        except UnicodeDecodeError:
            decoded = content.decode("iso-8859-1", errors="replace")

    reader = csv.DictReader(io.StringIO(decoded))

    results = {"imported": 0, "skipped": 0, "errors": []}

    for i, row in enumerate(reader):
        try:
            # Normalize column names safely to avoid NoneType crash on trailing commas
            normalized = {}
            for k, v in row.items():
                if k is None: continue
                safe_key = str(k).lower().strip().replace(" ", "_")
                safe_val = str(v).strip() if v is not None else ""
                normalized[safe_key] = safe_val
            email = normalized.get("email", "")
            if not email:
                results["errors"].append(f"Row {i+2}: missing email")
                continue

            # Extract natively without joining or splitting
            data = LeadCreate(
                email=email,
                full_name=normalized.get("full_name", "").strip(),
                first_name=normalized.get("first_name", "").strip(),
                last_name=normalized.get("last_name", "").strip(),
                title=normalized.get("title") or normalized.get("job_title"),
                company_name=normalized.get("company_name") or normalized.get("company"),
                company_domain=normalized.get("website") or normalized.get("company_domain") or normalized.get("domain"),
                company_funding_stage=normalized.get("funding_stage") or normalized.get("company_funding_stage"),
                company_size=normalized.get("company_size") or normalized.get("employees"),
                linkedin_url=normalized.get("linkedin") or normalized.get("linkedin_url"),
                location=normalized.get("location"),
                phone_number=normalized.get("phone_number") or normalized.get("phone") or normalized.get("mobile"),
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

@router.delete("/{lead_id}")
async def delete_lead(lead_id: str, db: AsyncSession = Depends(get_db)):
    """Soft deletes a lead so it is removed from UI without breaking existing email foreign keys."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead.is_suppressed = True
    await db.commit()
    return {"message": "Lead deleted successfully"}

@router.delete("/")
async def delete_all_leads(db: AsyncSession = Depends(get_db)):
    """Soft deletes all leads."""
    from sqlalchemy import update
    await db.execute(
        update(Lead)
        .where(Lead.is_suppressed == False)
        .values(is_suppressed=True)
    )
    await db.commit()
    return {"message": "All leads deleted successfully"}
