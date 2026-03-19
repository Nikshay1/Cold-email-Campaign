from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models import AppConfig

router = APIRouter()

class SettingsUpdate(BaseModel):
    groq_api_key: Optional[str] = None
    groq_model: str

class SettingsResponse(BaseModel):
    groq_api_key: Optional[str] = ""
    groq_model: str

@router.get("/", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AppConfig).limit(1))
    config = result.scalar_one_or_none()
    
    if not config:
        config = AppConfig(id="singleton", groq_model="llama-3.3-70b-versatile")
        db.add(config)
        await db.commit()
        await db.refresh(config)
    
    # Mask key for frontend safety
    masked_key = ""
    if config.groq_api_key:
        masked_key = config.groq_api_key[:8] + "********************************" if len(config.groq_api_key) > 8 else "***"
        
    return SettingsResponse(
        groq_api_key=masked_key,
        groq_model=config.groq_model
    )

@router.post("/")
async def update_settings(data: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AppConfig).limit(1))
    config = result.scalar_one_or_none()
    
    if not config:
        config = AppConfig(id="singleton")
        db.add(config)
    
    # Only update real API key if it's not the masked string
    if data.groq_api_key and not data.groq_api_key.endswith("*"):
        config.groq_api_key = data.groq_api_key
    elif not data.groq_api_key:
        config.groq_api_key = None
        
    config.groq_model = data.groq_model
    
    await db.commit()
    return {"message": "Settings updated"}
