import json
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from groq import AsyncGroq

from app.models import AppConfig

logger = logging.getLogger(__name__)

async def classify_reply(reply_text: str, db: AsyncSession) -> dict:
    """Uses Groq to classify a cold email reply if API key is present."""
    fallback = {
        "classification": "INTERESTED",
        "confidence": 1.0,
        "summary": "Manual review required. AI engine disabled or no API key.",
        "talking_points": []
    }
    
    result = await db.execute(select(AppConfig).limit(1))
    config = result.scalar_one_or_none()
    
    if not config or not config.groq_api_key or config.groq_api_key.endswith("*"):
        return fallback

    try:
        client = AsyncGroq(api_key=config.groq_api_key)
        
        prompt = f"""You are an expert sales AI. Analyze this reply from a prospect to a cold email campaign:
"{reply_text}"

You must return ONLY a raw JSON object (no markdown, no backticks).
Requirements:
1. classification must be exactly one of: INTERESTED, NOT_NOW, WRONG_PERSON, UNSUBSCRIBE, OTHER
2. confidence is a float from 0.0 to 1.0
3. summary is a single short sentence explaining their response
4. talking_points is an array of 0 to 3 brief suggestions on how to reply

JSON Format:
{{
  "classification": "INTERESTED",
  "confidence": 0.95,
  "summary": "They want to schedule a call.",
  "talking_points": ["Suggest 2 times", "Send agenda"]
}}
"""
        
        response = await client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=config.groq_model,
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=256
        )
        
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from Groq")
            
        data = json.loads(content)
        
        # Ensure enum safeties
        valid_classes = {"INTERESTED", "NOT_NOW", "WRONG_PERSON", "UNSUBSCRIBE", "OTHER"}
        if data.get("classification") not in valid_classes:
            data["classification"] = "OTHER"
            
        return data
        
    except Exception as e:
        logger.error(f"Groq classification failed: {e}")
        return fallback
