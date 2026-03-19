"""Claude-powered reply classifier (triage only — no auto-response)."""

import json
import logging
from typing import Optional
from groq import AsyncGroq

from app.config import get_settings
from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models import AppConfig

settings = get_settings()
logger = logging.getLogger(__name__)

async def _get_groq_config():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AppConfig).limit(1))
        config = result.scalar_one_or_none()
        if not config:
            return settings.groq_api_key, settings.groq_model
        return config.groq_api_key or settings.groq_api_key, config.groq_model


CLASSIFIER_SYSTEM = """You classify cold email replies for a startup founder pitching VCs in India.
Your job is to triage the reply so the founder can prioritize his response.
IMPORTANT: The founder always replies personally. You never generate a response. Only classify.

Categories:
- INTERESTED: Any positive signal — open to a call, wants more info, curious, asks questions
- NOT_NOW: Timing issue — busy, not the right time, check back later
- WRONG_PERSON: Reply directs to someone else, or they're not the right contact
- UNSUBSCRIBE: Explicit opt-out, remove me, stop emailing, not interested (clear rejection)
- OTHER: Unclear intent, auto-reply, out-of-office, ambiguous"""


async def classify_reply(reply_text: str) -> dict:
    """Classify a reply using Claude. Returns triage data for founder."""
    api_key, model = await _get_groq_config()
    
    if not api_key or api_key.startswith("gsk..."):
        return _mock_classification(reply_text)

    try:
        client = AsyncGroq(api_key=api_key)

        prompt = f"""Classify this cold email reply:

---
{reply_text[:2000]}
---

Return JSON only:
{{
  "classification": "INTERESTED",
  "confidence": 0.92,
  "summary": "One sentence describing what they said",
  "talking_points": ["point 1 for founder", "point 2", "point 3"]
}}

Rules for talking_points:
- Provide 2-4 bullet points the founder should address in his personal reply
- Only if classification is INTERESTED or NOT_NOW — otherwise empty list
- Be specific to what the VC said"""

        message = await client.chat.completions.create(
            model=model,
            max_tokens=300,
            messages=[
                {"role": "system", "content": CLASSIFIER_SYSTEM},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
        )

        text = message.choices[0].message.content.strip()
        data = json.loads(text)
        return {
            "classification": data.get("classification", "OTHER"),
            "confidence": float(data.get("confidence", 0.7)),
            "summary": data.get("summary", "Reply received"),
            "talking_points": data.get("talking_points", []),
        }

    except json.JSONDecodeError as e:
        logger.error(f"Claude classifier returned invalid JSON: {e}")
        return _mock_classification(reply_text)
    except Exception as e:
        logger.error(f"Claude classifier failed: {e}")
        return _mock_classification(reply_text)


def _mock_classification(text: str) -> dict:
    """Mock classification for development."""
    text_lower = text.lower()
    if any(w in text_lower for w in ["interested", "call", "more info", "tell me", "happy to", "sure", "yes"]):
        return {
            "classification": "INTERESTED",
            "confidence": 0.88,
            "summary": "Prospect seems interested in learning more",
            "talking_points": ["Explain Cortexa's core value prop", "Mention relevant traction", "Propose a time"],
        }
    elif any(w in text_lower for w in ["unsubscribe", "remove", "stop", "don't contact", "not interested"]):
        return {
            "classification": "UNSUBSCRIBE",
            "confidence": 0.97,
            "summary": "Prospect wants to be removed from outreach",
            "talking_points": [],
        }
    elif any(w in text_lower for w in ["not now", "busy", "later", "next quarter", "right now"]):
        return {
            "classification": "NOT_NOW",
            "confidence": 0.85,
            "summary": "Timing is not right, suggested following up later",
            "talking_points": ["Acknowledge their timing", "Ask when to reconnect", "Leave the door open"],
        }
    else:
        return {
            "classification": "OTHER",
            "confidence": 0.60,
            "summary": "Reply received — review needed",
            "talking_points": [],
        }
