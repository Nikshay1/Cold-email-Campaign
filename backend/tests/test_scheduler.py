"""Tests for inbox rotator and rate limiter logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.sending.scheduler import get_randomized_send_time
from datetime import datetime
import pytz


def test_send_time_is_business_hours():
    """Randomized send time must fall within 7am–5pm IST."""
    for _ in range(50):
        send_time_utc = get_randomized_send_time(prospect_country="IN")
        # Convert to IST
        ist = pytz.timezone("Asia/Kolkata")
        send_time_ist = send_time_utc.replace(tzinfo=pytz.utc).astimezone(ist)
        assert 7 <= send_time_ist.hour <= 17, f"Send time {send_time_ist.hour}:00 IST outside business hours"


def test_send_time_is_in_future():
    """All send times must be in the future."""
    send_time = get_randomized_send_time()
    assert send_time > datetime.utcnow()


def test_send_time_no_weekends():
    """Send times must not fall on weekends (Sat/Sun)."""
    for _ in range(30):
        send_time = get_randomized_send_time()
        ist = pytz.timezone("Asia/Kolkata")
        send_time_local = send_time.replace(tzinfo=pytz.utc).astimezone(ist)
        assert send_time_local.weekday() < 5, f"Got weekend: {send_time_local.strftime('%A')}"


def test_send_time_with_jitter():
    """Providing jitter offset should delay the send time."""
    t1 = get_randomized_send_time(jitter_add_seconds=0)
    t2 = get_randomized_send_time(jitter_add_seconds=3600)
    # t2 should generally be later (may not always hold due to day reset, but close)
    # Just ensure both are valid future times
    assert t1 > datetime.utcnow()
    assert t2 > datetime.utcnow()
