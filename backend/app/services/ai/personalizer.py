"""Claude-powered email personalization engine."""

import json
import logging
import hashlib
from dataclasses import dataclass, field
from typing import Optional
import redis.asyncio as aioredis

from app.config import get_settings
from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models import AppConfig
from app.models import Lead

settings = get_settings()
logger = logging.getLogger(__name__)

async def _get_groq_config():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AppConfig).limit(1))
        config = result.scalar_one_or_none()
        if not config:
            return settings.groq_api_key, settings.groq_model
        return config.groq_api_key or settings.groq_api_key, config.groq_model

CACHE_TTL = 7 * 24 * 3600  # 7 days


@dataclass
class PersonalizedEmail:
    subject: str
    body: str
    personalization_score: float
    subject_variants: list[str] = field(default_factory=list)
    variant_id: str = "v1"


SYSTEM_PROMPT = """You are a world-class cold email copywriter for a startup founder named Nikshay from Cortexa Labs.
Your emails:
- Sound like they came from a real human, not a robot or AI
- Are short (50–80 words for body), punchy, and direct
- Open with a hyper-specific observation about the prospect — NOT a generic compliment
- Have ONE clear call to action — a 15-minute call
- Never use buzzwords: synergy, leverage, game-changer, disruptive, innovative, revolutionary
- Never start with "I" as the first word
- Have a conversational, peer-to-peer tone — like a peer, not a sales rep
- Are optimized for mobile reading (short paragraphs, 1-2 sentences each)
- Never include attachments or multiple links"""


async def get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, decode_responses=True)


def _cache_key(lead_id: str, campaign_id: str) -> str:
    return f"email_draft:{lead_id}:{campaign_id}"


async def personalize_email(
    lead: Lead,
    campaign_id: str,
    value_proposition: str,
    pain_point: str,
    sequence_step: int = 1,
) -> PersonalizedEmail:
    """Full personalization chain. Returns cached result if exists."""
    redis = await get_redis()
    key = _cache_key(lead.id, campaign_id)

    cached = await redis.get(key)
    if cached and sequence_step == 1:
        logger.debug(f"Cache hit personalization for lead {lead.id}")
        data = json.loads(cached)
        return PersonalizedEmail(**data)

    api_key, model = await _get_groq_config()
    
    if not api_key or api_key.startswith("gsk..."):
        return _mock_email(lead, sequence_step)

    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=api_key)

        # Step 1: Generate opening line
        opening_line = await _generate_opening_line(client, model, lead)

        # Step 2: Generate email body
        body = await _generate_body(client, model, lead, opening_line, value_proposition, pain_point, sequence_step)

        # Step 3: Generate subject variants
        subject_variants = await _generate_subjects(client, model, body)

        # Step 4: Score and optionally rewrite
        score = await _score_email(client, model, body, subject_variants[0])

        email = PersonalizedEmail(
            subject=subject_variants[0],
            body=body,
            personalization_score=score,
            subject_variants=subject_variants,
        )

        # Cache only the initial email (step 1)
        if sequence_step == 1:
            await redis.setex(key, CACHE_TTL, json.dumps({
                "subject": email.subject,
                "body": email.body,
                "personalization_score": email.personalization_score,
                "subject_variants": email.subject_variants,
                "variant_id": email.variant_id,
            }))

        return email

    except Exception as e:
        logger.error(f"Claude personalization failed for lead {lead.id}: {e}")
        return _mock_email(lead, sequence_step)


async def _generate_opening_line(client, model: str, lead: Lead) -> str:
    prompt = f"""Given this lead context:
- Name: {lead.first_name} {lead.last_name or ''}
- Title: {lead.title or 'N/A'} at {lead.company_name or 'N/A'}
- LinkedIn Post: "{lead.linkedin_recent_post or 'N/A'}"
- Company News: "{lead.company_recent_news or 'N/A'}"
- Website: "{lead.company_website_summary or 'N/A'}"
- Tech Stack: {', '.join(lead.tech_stack or []) or 'N/A'}

Write ONE opening sentence (max 20 words) that:
1. References something SPECIFIC about them or their company
2. Shows you actually did your research (cite a fact, quote, or observation)
3. Flows naturally into a cold email
4. Is NOT a compliment — it's an observation, question, or reference to their work
5. Does not start with "I"

Return ONLY the sentence. No explanation, no quotes around it."""

    response = await client.chat.completions.create(
        model=model,
        max_tokens=100,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
    )
    return response.choices[0].message.content.strip()


async def _generate_body(
    client, model: str, lead: Lead, opening_line: str,
    value_proposition: str, pain_point: str, step: int
) -> str:
    step_guide = {
        1: "Initial outreach — introduce yourself, mention the problem, ask for a 15-min call",
        2: "Follow-up #1 — reference first email briefly, add ONE new insight or stat",
        3: "Follow-up #2 — different angle, share a quick result or relevant case",
        4: "Follow-up #3 — last check-in, very short, acknowledge they're probably busy",
        5: "Breakup email — acknowledge they're not interested, leave the door open, zero pressure",
    }.get(step, "Initial outreach")

    prompt = f"""Write a cold email (step {step}/5 in a sequence).
Opening line (already written, use as-is): "{opening_line}"

Context:
- Sender: Nikshay from Cortexa Labs (AI automation for outbound sales)
- Recipient: {lead.first_name}, {lead.title or 'professional'} at {lead.company_name or 'their company'}
- Pain point: {pain_point}
- What we offer: {value_proposition}
- Step: {step_guide}

Rules:
- Max 80 words total (including the opening line above)
- Start directly with the opening line
- No "Dear" or "Hi" salutation — jump straight in
- 2-3 short paragraphs max
- CTA: ask for a quick 15-min call. Make it feel low-stakes ("worth a quick chat?")
- End with a soft question, not a demand
- Zero buzzwords
- Plain text only — no markdown, no bullet points in the email body

Return ONLY the email body. No subject line. No signature. No explanation."""

    response = await client.chat.completions.create(
        model=model,
        max_tokens=300,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
    )
    return response.choices[0].message.content.strip()


async def _generate_subjects(client, model: str, body: str) -> list[str]:
    prompt = f"""For this cold email body:
---
{body[:500]}
---

Write 3 subject line options:
1. Curiosity-gap style (no clickbait)
2. Direct, benefit-focused  
3. First-name personalized (use {{first_name}} as placeholder)

Rules:
- Max 6 words each
- No emojis
- No ALL CAPS
- No spam words: free, guarantee, urgent, act now, limited time
- Sound human and natural

Return as JSON only: {{"options": ["...", "...", "..."]}}"""

    response = await client.chat.completions.create(
        model=model,
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    try:
        text = response.choices[0].message.content.strip()
        data = json.loads(text)
        return data.get("options", [text, text, text])
    except json.JSONDecodeError:
        return [response.choices[0].message.content.strip()[:60]] * 3


async def _score_email(client, model: str, body: str, subject: str) -> float:
    prompt = f"""Score this cold email strictly on a scale of 1–10 for each dimension:
- Personalization (feels written for a specific person, not generic)
- Clarity (ask is obvious, easy to understand)
- Tone (human, not salesy or corporate)
- Brevity (short enough to read in 10 seconds)

Subject: {subject}
Body: {body}

Return JSON only: {{"personalization": 8, "clarity": 9, "tone": 8, "brevity": 9, "overall": 8.5}}"""

    try:
        response = await client.chat.completions.create(
            model=model,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content.strip())
        return float(data.get("overall", 7.5))
    except Exception:
        return 7.5


def _mock_email(lead: Lead, step: int = 1) -> PersonalizedEmail:
    """Mock personalized email for development."""
    name = lead.first_name or "there"
    company = lead.company_name or "your company"

    bodies = {
        1: f"Noticed {company} is scaling its outbound — that's exactly when teams hit deliverability walls.\n\nWe built Cortexa to solve that: AI-personalized cold emails across rotating inboxes, without landing in spam.\n\nWorth a 15-min chat to see if it fits what you're building?",
        2: f"Just wanted to bump this up in case it got buried.\n\nOne thing I didn't mention — Cortexa handles inbox warmup automatically, so you don't have to babysit domain health.\n\nStill open to a quick call this week?",
        3: f"Last thing I'll share: teams using Cortexa typically see >45% open rates in their first month.\n\nIf outbound is a priority for {company}, happy to show you exactly how it works in 15 mins.",
        4: f"I'll keep this short — I know you're slammed.\n\nIf AI-powered outreach isn't the right fit right now, totally understand. Just didn't want to miss the chance to connect.",
        5: f"I've reached out a few times and I don't want to clutter your inbox.\n\nIf the timing ever works for Cortexa, my door's always open. Best of luck with {company}!",
    }

    subjects = ["Quick question", f"Re: outreach at {company}", f"{name} — 2 min?"]

    return PersonalizedEmail(
        subject=subjects[0],
        body=bodies.get(step, bodies[1]),
        personalization_score=7.8,
        subject_variants=subjects,
    )
