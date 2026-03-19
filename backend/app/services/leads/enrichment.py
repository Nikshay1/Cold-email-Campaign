"""Hunter.io enrichment with Redis caching."""

import json
import logging
import httpx
import redis.asyncio as aioredis
from typing import Optional

from app.config import get_settings
from app.models import Lead

settings = get_settings()
logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 90 * 24 * 3600  # 90 days


async def get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def enrich_lead(lead: Lead) -> dict:
    """Enrich a lead using Hunter.io. Caches results per company domain."""
    if not settings.hunter_io_api_key:
        logger.warning("Hunter.io API key not set — returning mock enrichment")
        return _mock_enrichment(lead)

    redis = await get_redis()
    cache_key = f"enrichment:{lead.company_domain or lead.email}"

    cached = await redis.get(cache_key)
    if cached:
        logger.debug(f"Cache hit for {cache_key}")
        return json.loads(cached)

    result = {}

    # Verify email deliverability
    try:
        email_data = await _verify_email(lead.email)
        result["email_verified"] = email_data.get("result") == "deliverable"
        result["email_score"] = email_data.get("score", 0)
    except Exception as e:
        logger.error(f"Email verify failed for {lead.email}: {e}")
        result["email_verified"] = False

    # Company enrichment (by domain)
    if lead.company_domain:
        try:
            company_data = await _enrich_company(lead.company_domain)
            result.update(company_data)
        except Exception as e:
            logger.error(f"Company enrich failed for {lead.company_domain}: {e}")

    await redis.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(result))
    return result


async def _verify_email(email: str) -> dict:
    url = "https://api.hunter.io/v2/email-verifier"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params={"email": email, "api_key": settings.hunter_io_api_key})
        resp.raise_for_status()
        return resp.json().get("data", {})


async def _enrich_company(domain: str) -> dict:
    url = "https://api.hunter.io/v2/domain-search"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params={
            "domain": domain,
            "api_key": settings.hunter_io_api_key,
            "limit": 1,
        })
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return {
            "company_name": data.get("organization"),
            "company_industry": data.get("industry"),
            "company_size": str(data.get("company", {}).get("size", "")),
            "company_website_summary": data.get("description"),
            "tech_stack": [t.get("name") for t in data.get("technologies", [])],
        }


def _mock_enrichment(lead: Lead) -> dict:
    """Mock enrichment for development without API keys."""
    return {
        "email_verified": True,
        "email_score": 85,
        "company_industry": "Technology",
        "company_size": "51-200",
        "tech_stack": ["HubSpot", "Segment"],
        "company_website_summary": f"{lead.company_name or 'The company'} builds software products.",
    }
