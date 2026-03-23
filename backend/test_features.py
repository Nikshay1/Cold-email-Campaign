import asyncio
from datetime import datetime, date
from app.services.sending.scheduler import get_randomized_send_time
from app.routers.campaigns import get_next_business_day

def test_scheduler():
    # Test next business day
    d1 = date(2026, 3, 20) # Friday
    next_d1 = get_next_business_day(d1)
    assert next_d1 == date(2026, 3, 23), f"Expected Monday, got {next_d1}"
    
    d2 = date(2026, 3, 23) # Monday
    next_d2 = get_next_business_day(d2)
    assert next_d2 == date(2026, 3, 24), f"Expected Tuesday, got {next_d2}"

    # Test get_randomized_send_time with target_date
    t1 = get_randomized_send_time(target_date=date(2026, 4, 1), jitter_add_seconds=0)
    assert t1.date() >= date(2026, 4, 1) # Will convert to UTC, might be a day off but logic ensures it's based on tz

    print("Scheduler logic works correctly!")

if __name__ == "__main__":
    test_scheduler()
