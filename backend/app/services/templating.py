"""String-based templating engine."""

import re
from app.models import Lead

def render_template(template: str, lead: Lead) -> str:
    """
    Replaces variables like [NAME] or [COMPANY] with the actual lead data.
    """
    if not template:
        return ""
        
    replacements = {
        r"\[NAME\]": lead.first_name or lead.full_name or "",
        r"\[FIRST_NAME\]": lead.first_name or "",
        r"\[FIRST NAME\]": lead.first_name or "",
        r"\[LAST_NAME\]": lead.last_name or "",
        r"\[LAST NAME\]": lead.last_name or "",
        r"\[EMAIL\]": lead.email or "",
        r"\[FULL_NAME\]": lead.full_name or f"{lead.first_name or ''} {lead.last_name or ''}".strip(),
        r"\[FULL NAME\]": lead.full_name or f"{lead.first_name or ''} {lead.last_name or ''}".strip(),
        r"\[COMPANY\]": lead.company_name or "your company",
        r"\[COMPANY_NAME\]": lead.company_name or "your company",
        r"\[COMPANY NAME\]": lead.company_name or "your company",
        r"\[TITLE\]": lead.title or "your role",
        r"\[INDUSTRY\]": lead.company_industry or "your industry",
        r"\[LOCATION\]": lead.location or "your location",
        r"\[PHONE\]": lead.phone_number or "your phone number",
        r"\[WEBSITE\]": lead.company_domain or "your website",
    }
    
    rendered = template
    for pattern, value in replacements.items():
        # Case insensitive replacement for placeholders like [name], [Name]
        rendered = re.sub(pattern, str(value), rendered, flags=re.IGNORECASE)
        
    return rendered
