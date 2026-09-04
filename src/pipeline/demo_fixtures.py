"""Mocked candidate data for DEMO_MODE (spec section 38): lets the whole
pipeline run end-to-end with no search/Blogger/Telegram/AI network calls
(when combined with AI_PROVIDER=mock)."""
from __future__ import annotations

from typing import Dict, List


def build_demo_candidates(topics: List[Dict]) -> List[Dict]:
    """Build a small set of fake but structurally realistic candidates,
    including duplicate coverage of the same events across sources, and a
    couple of weak/rejectable stories, so the demo proves out dedup +
    verification + rejection, not just the happy path."""
    if not topics:
        return []

    demo_events = [
        {
            "title": "شركة تقنية تطلق نموذج ذكاء اصطناعي جديد",
            "region": "Global", "country": "United States",
            "topic_hint": "topic_ai",
            "sources": [
                {"domain": "reuters.com", "tier": 1, "cred": 0.95},
                {"domain": "bbc.com", "tier": 2, "cred": 0.8},
                {"domain": "techcrunch.com", "tier": 3, "cred": 0.65},
            ],
        },
        {
            "title": "شركة ناشئة سعودية تجمع تمويلاً بقيمة 30 مليون دولار",
            "region": "Gulf", "country": "Saudi Arabia",
            "topic_hint": "topic_startups",
            "sources": [
                {"domain": "arabnews.com", "tier": 3, "cred": 0.65},
                {"domain": "reuters.com", "tier": 1, "cred": 0.95},
            ],
        },
        {
            "title": "فوز فريق كرة القدم الوطني في مباراة حاسمة",
            "region": "Arab World", "country": "Egypt",
            "topic_hint": "topic_sports_football",
            "sources": [
                {"domain": "espn.com", "tier": 3, "cred": 0.65},
                {"domain": "bbc.com", "tier": 2, "cred": 0.8},
            ],
        },
        {
            "title": "جامعة أوروبية تعلن عن اكتشاف علمي جديد",
            "region": "Europe", "country": "Germany",
            "topic_hint": "topic_research",
            "sources": [
                {"domain": "nytimes.com", "tier": 2, "cred": 0.8},
            ],
        },
        {
            "title": "شائعة غير مؤكدة حول استقالة مسؤول تنفيذي",
            "region": "Global", "country": "",
            "topic_hint": "topic_ceos",
            "sources": [
                {"domain": "randomblog.example", "tier": 4, "cred": 0.4},
            ],
        },
    ]

    candidates: List[Dict] = []
    topic_ids = {t["id"] for t in topics}
    for i, evt in enumerate(demo_events):
        topic_id = evt["topic_hint"] if evt["topic_hint"] in topic_ids else topics[i % len(topics)]["id"]
        for j, src in enumerate(evt["sources"]):
            candidates.append({
                "title": evt["title"],
                "summary": f"ملخص تجريبي للحدث رقم {i} من المصدر {src['domain']}.",
                "url": f"https://{src['domain']}/demo-article-{i}-{j}",
                "domain": src["domain"],
                "source_tier": src["tier"],
                "credibility_score": src["cred"],
                "published_at": None,
                "topic_id": topic_id,
                "region": evt["region"],
                "country": evt["country"],
                "entities": [],
            })
    return candidates
