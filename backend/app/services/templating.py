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
        r"\[NAME\]": lead.first_name or "",
        r"\[FIRST_NAME\]": lead.first_name or "",
        r"\[LAST_NAME\]": lead.last_name or "",
        r"\[COMPANY\]": lead.company_name or "your company",
        r"\[COMPANY_NAME\]": lead.company_name or "your company",
        r"\[TITLE\]": lead.title or "your role",
        r"\[INDUSTRY\]": lead.company_industry or "your industry",
    }
    
    rendered = template
    for pattern, value in replacements.items():
        # Case insensitive replacement for placeholders like [name], [Name]
        rendered = re.sub(pattern, str(value), rendered, flags=re.IGNORECASE)
        
    return rendered
