"""Tests for lead scoring engine."""

import pytest
from app.models import Lead, LeadTier
from app.services.leads.scoring import score_lead, assign_tier


def make_lead(**kwargs) -> Lead:
    defaults = dict(
        id="test-id",
        email="test@example.com",
        first_name="Test",
    )
    defaults.update(kwargs)
    return Lead(**defaults)


def test_tier1_vc_partner():
    lead = make_lead(
        title="Partner",
        company_name="Sequoia India",
        company_funding_stage="Fund",
        company_size="51-200",
        tech_stack=["HubSpot", "Segment"],
        email_verified=True,
        linkedin_url="https://linkedin.com/in/test",
        company_domain="sequoiaindia.com",
    )
    score = score_lead(lead)
    assert score >= 75
    assert assign_tier(score) == LeadTier.TIER1


def test_tier2_mid_seniority():
    lead = make_lead(
        title="Director of Growth",
        company_funding_stage="Series A",
        company_size="201-500",
    )
    score = score_lead(lead)
    assert 45 <= score < 75
    assert assign_tier(score) == LeadTier.TIER2


def test_tier3_no_data():
    lead = make_lead(email="nobody@unknown.com", first_name="No")
    score = score_lead(lead)
    assert score < 45
    assert assign_tier(score) == LeadTier.TIER3


def test_score_capped_at_100():
    lead = make_lead(
        title="CEO",
        company_funding_stage="Series B",
        company_size="51-200",
        tech_stack=["HubSpot", "Segment", "Intercom", "Apollo", "Clay", "Instantly"],
        email_verified=True,
        linkedin_url="https://linkedin.com/in/test",
        company_domain="acme.com",
    )
    score = score_lead(lead)
    assert score <= 100


def test_no_funding_stage():
    lead = make_lead(title="VP of Sales", company_size="11-50")
    score = score_lead(lead)
    assert score >= 30  # Seniority + size should still give decent score


def test_tech_stack_overlap():
    lead = make_lead(tech_stack=["HubSpot", "Segment", "Apollo"])
    score_with = score_lead(lead)
    lead2 = make_lead(tech_stack=["Excel", "Notepad"])
    score_without = score_lead(lead2)
    assert score_with > score_without
