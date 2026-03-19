"""Google OAuth2 flow for Gmail inbox authorization."""

import urllib.parse
from datetime import datetime, timedelta
import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Inbox, InboxHealth
from app.config import get_settings

settings = get_settings()
router = APIRouter()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


@router.get("/google/authorize")
async def google_authorize(inbox_id: str, db: AsyncSession = Depends(get_db)):
    """Start Google OAuth flow for an inbox."""
    if not settings.google_client_id:
        raise HTTPException(status_code=400, detail="Google OAuth not configured")

    result = await db.execute(select(Inbox).where(Inbox.id == inbox_id))
    inbox = result.scalar_one_or_none()
    
    # We craft the authorization URL manually. This bypasses google_auth_oauthlib's 
    # forced PKCE mechanics which require persistent server-side session storage.
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.google_client_id}"
        f"&redirect_uri={urllib.parse.quote(settings.google_redirect_uri)}"
        "&response_type=code"
        f"&scope={urllib.parse.quote(' '.join(SCOPES))}"
        "&access_type=offline"
        "&prompt=consent"
        f"&state={inbox_id}"
    )

    if inbox:
        auth_url += f"&login_hint={urllib.parse.quote(inbox.email)}"

    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    """Handle OAuth callback and save tokens to inbox."""
    inbox_id = state
    result = await db.execute(select(Inbox).where(Inbox.id == inbox_id))
    inbox = result.scalar_one_or_none()
    
    if not inbox:
        raise HTTPException(status_code=404, detail="Inbox not found")

    # Exchange the code for tokens securely
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.google_redirect_uri,
            }
        )
    
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Google OAuth Failed. {resp.text}")

    data = resp.json()
    inbox.gmail_access_token = data.get("access_token")
    
    # Google only returns refresh_token on the first authorization or if prompt=consent is used.
    if data.get("refresh_token"):
        inbox.gmail_refresh_token = data.get("refresh_token")
        
    expires_in = data.get("expires_in", 3599)
    inbox.gmail_token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
    
    inbox.health = InboxHealth.GOOD
    await db.commit()

    return RedirectResponse(url="http://localhost:3000/inboxes?success=1")
