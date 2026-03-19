"""Lead ICP scoring engine."""

from app.models import Lead, LeadTier

ICP_TECH_STACK = {
    "hubspot", "salesforce", "apollo", "outreach", "salesloft",
    "intercom", "segment", "mixpanel", "amplitude", "clearbit",
    "zapier", "clay", "instantly", "smartlead",
}

ICP_FUNDING_STAGES = {
    "pre-seed": 10,
    "seed": 20,
    "series a": 35,
    "series b": 35,
    "series c": 25,
    "growth": 20,
}

ICP_SENIORITY_KEYWORDS = [
    "founder", "co-founder", "ceo", "cto", "cmo", "cro",
    "vp", "vice president", "head of", "director", "partner",
    "general partner", "managing director", "principal",
]

ICP_COMPANY_SIZES = {
    "1-10": 5,
    "11-50": 15,
    "51-200": 25,
    "201-500": 20,
    "501-1000": 10,
    "1000+": 5,
    "10001+": 2,
}


def score_lead(lead: Lead) -> int:
    score = 0

    # Funding stage (max 35 pts)
    if lead.company_funding_stage:
        stage_key = lead.company_funding_stage.lower().strip()
        score += ICP_FUNDING_STAGES.get(stage_key, 0)

    # Seniority (max 30 pts)
    if lead.title:
        title_lower = lead.title.lower()
        if any(kw in title_lower for kw in ICP_SENIORITY_KEYWORDS):
            score += 30

    # Company size (max 25 pts)
    if lead.company_size:
        size_key = lead.company_size.strip()
        score += ICP_COMPANY_SIZES.get(size_key, 0)

    # Tech stack overlap (max 15 pts)
    if lead.tech_stack:
        overlap = set(t.lower() for t in lead.tech_stack) & ICP_TECH_STACK
        if overlap:
            score += min(15, len(overlap) * 5)

    # Email verified (bonus 5 pts)
    if lead.email_verified:
        score += 5

    # LinkedIn URL present (bonus 5 pts)
    if lead.linkedin_url:
        score += 5

    # Company domain known (bonus 5 pts)
    if lead.company_domain:
        score += 5

    return min(score, 100)


def assign_tier(score: int) -> LeadTier:
    if score >= 75:
        return LeadTier.TIER1
    elif score >= 45:
        return LeadTier.TIER2
    else:
        return LeadTier.TIER3
