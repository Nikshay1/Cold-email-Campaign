"""Send-time randomizer: business hours + human-like jitter."""

import random
import pytz
from datetime import datetime, timedelta

from app.config import get_settings

settings = get_settings()

TIMEZONE_BY_COUNTRY = {
    "IN": "Asia/Kolkata",
    "US": "America/New_York",
    "GB": "Europe/London",
    "SG": "Asia/Singapore",
    "AU": "Australia/Sydney",
}


def get_randomized_send_time(
    base: datetime | None = None,
    prospect_country: str = "IN",
    jitter_add_seconds: int = 0,
) -> datetime:
    """
    Returns a randomized send datetime:
    - Within business hours (settings.send_hour_min to send_hour_max) in prospect's timezone
    - With 1–8 minute jitter between sends
    - Always in the future relative to `base`
    """
    base = base or datetime.utcnow()
    tz_name = TIMEZONE_BY_COUNTRY.get(prospect_country, "Asia/Kolkata")
    tz = pytz.timezone(tz_name)

    # Pick a random business hour
    hour = random.randint(settings.send_hour_min, settings.send_hour_max - 1)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    # Start from tomorrow if the chosen time already passed today
    local_now = datetime.now(tz)
    candidate = local_now.replace(hour=hour, minute=minute, second=second, microsecond=0)
    if candidate <= local_now:
        candidate += timedelta(days=1)

    # Skip weekends
    while candidate.weekday() >= 5:  # 5=Sat, 6=Sun
        candidate += timedelta(days=1)

    # Add human jitter
    jitter = random.randint(settings.jitter_min_seconds, settings.jitter_max_seconds)
    candidate += timedelta(seconds=jitter + jitter_add_seconds)

    # Convert back to UTC for storage
    return candidate.astimezone(pytz.utc).replace(tzinfo=None)
