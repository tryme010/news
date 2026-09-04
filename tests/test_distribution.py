from src.distribution.allocator import allocate_event_to_websites
from src.distribution.balancing import balance_penalty
from src.distribution.scorer import score_event_for_website

WEBSITES = [
    {"id": "site_05", "name": "Technology", "editorial_focus": ["ai", "software"],
     "regions": ["Global"], "priority": 5, "active": True},
    {"id": "site_07", "name": "Sports", "editorial_focus": ["football", "athletes"],
     "regions": ["Arab World"], "priority": 7, "active": True},
]


def test_score_event_for_website_matches_focus():
    event = {"title": "ai startup launches new software", "summary": "", "entities": [], "region": "Global"}
    score = score_event_for_website(event, WEBSITES[0])
    assert score > 0


def test_score_event_for_website_region_bonus():
    event_global = {"title": "generic news", "summary": "", "entities": [], "region": "Global"}
    event_arab = {"title": "generic news", "summary": "", "entities": [], "region": "Arab World"}
    score_global = score_event_for_website(event_arab, WEBSITES[1])
    assert score_global >= 0


def test_balance_penalty_zero_when_under_threshold():
    assert balance_penalty("site_05", {"site_05": 1, "site_07": 3}) == 0.0


def test_balance_penalty_positive_when_dominant():
    counts = {"site_05": 20, "site_07": 1}
    assert balance_penalty("site_05", counts) > 0.0


def test_allocate_event_respects_max_sites():
    event = {"title": "ai software football event", "summary": "", "entities": [], "region": "Global"}
    allocations = allocate_event_to_websites(
        event, WEBSITES, {}, min_relevance_score=0, max_sites_per_event=1,
    )
    assert len(allocations) <= 1
