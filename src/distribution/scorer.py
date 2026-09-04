"""Score an event against every website's editorial focus/region to decide
relevance (spec section 26)."""
from __future__ import annotations

from typing import Dict, List


def score_event_for_website(event: Dict, website: Dict) -> float:
    """Score relevance of `event` for `website`.

    Primary signal is topic-based routing (event['topic_preferred_sites'],
    sourced from config/topics.json's `preferred_sites`), which is
    language-agnostic and works whether the article text is Arabic or
    English. Free-text editorial_focus keyword matching is used only as a
    secondary boost for English-language entity/title matches (useful when
    entities are proper nouns like "Apple", "AI", etc. that appear
    verbatim regardless of article language).
    """
    score = 0.0

    preferred_sites = event.get("topic_preferred_sites", [])
    if website.get("id") in preferred_sites:
        score += 55

    event_entities_text = " ".join(event.get("entities", [])).lower()
    event_title = (event.get("title", "") + " " + event.get("summary", "")).lower()

    focus_matches = sum(
        1 for focus in website.get("editorial_focus", [])
        if focus.replace("_", " ") in event_title or focus.replace("_", " ") in event_entities_text
    )
    score += min(focus_matches, 3) * 15  # up to 45, secondary signal

    event_region = event.get("region", "")
    event_country = event.get("country", "")
    site_regions = website.get("regions", [])
    if event_region in site_regions or event_country in site_regions:
        score += 25
    elif "Global" in site_regions:
        score += 10

    score += max(0, 6 - website.get("priority", 5)) * 1.5  # slight editorial priority nudge

    return min(100.0, score)


def score_event_for_all_websites(event: Dict, websites: List[Dict]) -> List[Dict]:
    scored = []
    for site in websites:
        if not site.get("active", True):
            continue
        scored.append({
            "website_id": site["id"],
            "website": site,
            "score": score_event_for_website(event, site),
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored
