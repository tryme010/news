from src.ai.mock_provider import MockProvider
from src.verification.scoring import cheap_prefilter, is_sensitive
from src.verification.verifier import score_to_status, verify_event_group


def test_is_sensitive_detects_keywords():
    assert is_sensitive("مقتل شخص في حادث", "")
    assert not is_sensitive("افتتاح معرض فني جديد", "")


def test_cheap_prefilter_rejects_single_low_quality_source():
    group = [{"title": "خبر غير مؤكد", "domain": "randomblog.example",
              "credibility_score": 0.15, "source_tier": 5}]
    result = cheap_prefilter(group)
    assert result["passes"] is False


def test_cheap_prefilter_passes_multi_source_credible_group():
    group = [
        {"title": "شركة تطلق منتجاً", "domain": "reuters.com", "credibility_score": 0.95, "source_tier": 1},
        {"title": "شركة تطلق منتجاً", "domain": "bbc.com", "credibility_score": 0.8, "source_tier": 2},
    ]
    result = cheap_prefilter(group)
    assert result["passes"] is True


def test_score_to_status_thresholds():
    assert score_to_status(10) == "reject"
    assert score_to_status(50) == "weak"
    assert score_to_status(70) == "review"
    assert score_to_status(85) == "good"
    assert score_to_status(95) == "strong"


def test_verify_event_group_with_mock_provider():
    ai = MockProvider()
    group = [
        {"title": "شركة تطلق منتجاً جديداً", "domain": "reuters.com",
         "credibility_score": 0.95, "source_tier": 1, "url": "https://reuters.com/x"},
        {"title": "شركة تطلق منتجاً جديداً", "domain": "bbc.com",
         "credibility_score": 0.8, "source_tier": 2, "url": "https://bbc.com/x"},
    ]
    result = verify_event_group(group, ai, min_score_to_publish=60)
    assert result["verification_score"] > 0
    assert "recommended_status" in result


def test_verify_event_group_exposes_rejection_reason_for_insufficient_sources():
    ai = MockProvider()
    group = [{
        "title": "مقتل شخص في حادث", "summary": "", "domain": "bbc.com",
        "credibility_score": 0.8, "source_tier": 2, "url": "https://bbc.com/x"
    }]
    result = verify_event_group(group, ai, min_score_to_publish=60)
    assert result["passes_publish_bar"] is False
    assert "insufficient_source_diversity" in result["reason"]


def test_sensitive_story_requires_two_credible_domains():
    group = [
        {"title": "اتهام خطير ضد مسؤول", "domain": "bbc.com", "source_tier": 2, "credibility_score": 0.8},
        {"title": "اتهام خطير ضد مسؤول", "domain": "randomblog.example", "source_tier": 4, "credibility_score": 0.4},
    ]
    result = cheap_prefilter(group)
    assert result["passes"] is False
    assert "tier1_3" in result["reason"]
