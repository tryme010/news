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


def test_cheap_prefilter_allows_one_credible_source_even_when_sensitive():
    group = [{
        "title": "Two people killed in explosion",
        "domain": "reuters.com",
        "credibility_score": 0.95,
        "source_tier": 1,
    }]
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


def test_verify_event_group_does_not_require_second_source_for_sensitive_news():
    class SensitiveProvider(MockProvider):
        def verify(self, prompt):
            return {
                "is_real_event": True,
                "is_recent": True,
                "is_newsworthy": True,
                "is_sensitive": True,
                "sufficient_source_support": True,
                "independent_source_count": 1,
                "confidence_notes": "Single credible source supports the event.",
                "verification_score": 85,
                "recommended_status": "good",
            }

    group = [{
        "title": "Two people killed in explosion",
        "domain": "reuters.com",
        "credibility_score": 0.95,
        "source_tier": 1,
        "url": "https://reuters.com/x",
    }]
    result = verify_event_group(group, SensitiveProvider(), min_score_to_publish=60)
    assert result["passes_publish_bar"] is True
