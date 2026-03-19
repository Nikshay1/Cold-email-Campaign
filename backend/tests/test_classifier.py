"""Tests for reply classifier (mocked Claude)."""

import pytest
from unittest.mock import AsyncMock, patch
from app.services.replies.classifier import _mock_classification


def test_classify_interested_keywords():
    text = "Hi! Yes, I'd be happy to jump on a call. What does your traction look like?"
    result = _mock_classification(text)
    assert result["classification"] == "INTERESTED"
    assert result["confidence"] > 0.8
    assert len(result["talking_points"]) > 0


def test_classify_unsubscribe():
    text = "Please stop emailing me. Unsubscribe me from your list."
    result = _mock_classification(text)
    assert result["classification"] == "UNSUBSCRIBE"
    assert result["confidence"] > 0.9
    assert result["talking_points"] == []


def test_classify_not_now():
    text = "Not the right time for us right now. Maybe next quarter."
    result = _mock_classification(text)
    assert result["classification"] == "NOT_NOW"
    assert result["confidence"] > 0.7


def test_classify_ambiguous():
    text = "Thanks for your message. I'll keep this on file."
    result = _mock_classification(text)
    assert result["classification"] in ["OTHER", "NOT_NOW", "INTERESTED"]
    assert "classification" in result
    assert "confidence" in result


def test_classifier_always_returns_required_fields():
    for text in ["yes", "no", "maybe", "", "Hello there"]:
        result = _mock_classification(text)
        assert "classification" in result
        assert "confidence" in result
        assert "summary" in result
        assert "talking_points" in result
        assert isinstance(result["talking_points"], list)
