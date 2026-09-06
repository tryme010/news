"""Combine all discovery providers into a normalized candidate list.

RSS items are fetched once and assigned to the most relevant topic instead
of being duplicated across every topic. Search results remain topic-specific.
Early URL deduplication keeps the verification stage small and fast.
"""
from __future__ import annotations

import logging
from typing import Dict, List

from src.discovery.queries import build_queries
from src.discovery.rss import fetch_rss_candidates
from src.discovery.search_engine import search_news
from src.discovery.source_registry import classify_domain
from src.deduplication.normalizer import normalize_url

logger = logging.getLogger("news_bot.discovery.candidate_builder")


def _topic_text(topic: Dict) -> str:
    """Build searchable text from a topic definition."""
    parts: List[str] = []

    for key in ("name", "title", "description", "category"):
        value = topic.get(key)
        if value:
            parts.append(str(value))

    for key in ("keywords", "aliases", "search_terms"):
        values = topic.get(key, [])
        if isinstance(values, list):
            parts.extend(str(value) for value in values if value)

    return " ".join(parts).lower()


def _candidate_text(item: Dict) -> str:
    """Build searchable text from a candidate."""
    parts = [
        item.get("title", ""),
        item.get("summary", ""),
    ]

    tags = item.get("tags", [])
    if isinstance(tags, list):
        parts.extend(str(tag) for tag in tags)

    return " ".join(str(part) for part in parts if part).lower()


TOPIC_ALIASES = {
    "topic_politics_arab": ["arab", "arab world", "middle east", "government", "president", "minister"],
    "topic_politics_global": ["politics", "president", "election", "elections", "diplomacy", "parliament", "government"],
    "topic_economy_global": ["economy", "economic", "inflation", "gdp", "interest rates", "central bank"],
    "topic_economy_arab": ["arab economy", "middle east economy", "gulf economy"],
    "topic_markets": ["stocks", "stock market", "shares", "trading", "wall street", "market"],
    "topic_companies": ["company", "companies", "corporate", "business", "earnings", "acquisition", "merger"],
    "topic_startups": ["startup", "startups", "venture capital", "funding", "seed round", "series a", "series b"],
    "topic_ai": ["artificial intelligence", "ai", "machine learning", "chatbot", "llm", "openai", "gemini"],
    "topic_technology": ["technology", "tech", "software", "gadgets", "device", "smartphone"],
    "topic_cybersecurity": ["cybersecurity", "cyber attack", "hack", "hacker", "ransomware", "data breach"],
    "topic_science": ["science", "scientist", "discovery", "research", "study"],
    "topic_medicine": ["medicine", "medical", "healthcare", "drug", "vaccine", "clinical trial"],
    "topic_sports_football": ["football", "soccer", "premier league", "champions league"],
    "topic_sports_basketball": ["basketball", "nba"],
    "topic_sports_tennis": ["tennis", "wimbledon", "us open", "roland garros"],
    "topic_entertainment": ["entertainment", "celebrity", "actor", "actress", "star"],
    "topic_cinema": ["film", "movie", "cinema", "box office"],
    "topic_music": ["music", "singer", "album", "concert"],
    "topic_tourism": ["tourism", "travel", "tourist", "hotel", "flight"],
    "topic_real_estate": ["real estate", "property", "housing", "home prices"],
    "topic_energy": ["energy", "oil", "gas", "opec", "electricity", "renewable"],
    "topic_climate": ["climate", "global warming", "emissions", "carbon"],
    "topic_environment": ["environment", "sustainability", "pollution", "wildlife"],
    "topic_space": ["space", "nasa", "rocket", "satellite", "astronaut"],
    "topic_transportation": ["transport", "aviation", "airline", "airport", "shipping", "railway"],
    "topic_digital_economy": ["e-commerce", "ecommerce", "digital economy", "online shopping", "fintech"],
    "topic_public_policy": ["policy", "regulation", "regulator", "law", "legislation"],
    "topic_africa": ["africa", "african", "nigeria", "kenya", "south africa", "egypt"],
    "topic_europe": ["europe", "european", "eu", "european union", "ukraine", "germany", "france"],
    "topic_asia": ["asia", "asian", "china", "japan", "india", "south korea", "indonesia"],
    "topic_americas": ["america", "american", "united states", "usa", "canada", "brazil", "mexico"],
    "topic_regional_gulf": ["gulf", "gcc", "saudi", "uae", "qatar", "kuwait", "bahrain", "oman"],
    "topic_regional_egypt": ["egypt", "egyptian", "cairo"],
    "topic_regional_saudi": ["saudi", "saudi arabia", "riyadh"],
    "topic_regional_uae": ["uae", "dubai", "abu dhabi", "emirates"],
    "topic_regional_qatar": ["qatar", "doha"],
    "topic_regional_kuwait": ["kuwait"],
    "topic_regional_bahrain": ["bahrain", "manama"],
    "topic_regional_oman": ["oman", "muscat"],
}


def _assign_rss_topic(item: Dict, topics: List[Dict]) -> Dict | None:
    """Assign an RSS candidate to the best relevant selected topic."""
    text = _candidate_text(item)
    best_topic: Dict | None = None
    best_score = 0

    for topic in topics:
        topic_text = _topic_text(topic)
        topic_id = topic.get("id", "")
        aliases = TOPIC_ALIASES.get(topic_id, [])
        terms = set(aliases)
        terms.update(
            term.strip()
            for term in topic_text.split()
            if len(term.strip()) >= 5 and term.strip() not in {"news", "global", "arab"}
        )
        score = sum(1 for term in terms if term and term in text)
        if score > best_score:
            best_score = score
            best_topic = topic

    # A world-news feed is allowed a conservative fallback to international
    # affairs, but only when that topic is part of this run's selected set.
    if best_topic is None and item.get("feed_topic_hint"):
        hint_id = item["feed_topic_hint"]
        best_topic = next((t for t in topics if t.get("id") == hint_id), None)

    return best_topic


def _normalize_candidate(item: Dict, topic: Dict) -> Dict | None:
    """Normalize and classify one candidate."""
    url = item.get("url", "")
    if not url:
        return None

    normalized = normalize_url(url)
    classification = classify_domain(normalized)

    return {
        **item,
        "url": normalized,
        "topic_id": topic["id"],
        "domain": classification["domain"],
        "source_tier": classification["tier"],
        "credibility_score": classification["credibility_score"],
    }


def discover_candidates(
    topics: List[Dict],
    demo_mode: bool = False,
    demo_fixtures: List[Dict] | None = None,
) -> List[Dict]:
    """Return a deduplicated list of raw candidates.

    RSS is fetched once and each RSS item is assigned to at most one topic.
    Search results are collected per topic and deduplicated immediately.
    """
    if demo_mode:
        return demo_fixtures or []

    candidates_by_url: Dict[str, Dict] = {}

    # ---------------------------------------------------------
    # 1. RSS discovery
    # ---------------------------------------------------------
    rss_candidates = fetch_rss_candidates()

    rss_assigned = 0
    rss_unmatched = 0

    for item in rss_candidates:
        topic = _assign_rss_topic(item, topics)

        if topic is None:
            rss_unmatched += 1
            continue

        candidate = _normalize_candidate(item, topic)

        if candidate is None:
            continue

        url = candidate["url"]

        if url not in candidates_by_url:
            candidates_by_url[url] = candidate
            rss_assigned += 1

    # ---------------------------------------------------------
    # 2. Search discovery
    # ---------------------------------------------------------
    search_count = 0

    for topic in topics:
        for query in build_queries(topic)[:4]:
            for item in search_news(query):
                candidate = _normalize_candidate(item, topic)

                if candidate is None:
                    continue

                url = candidate["url"]
                search_count += 1

                # Keep the first occurrence of the URL.
                # This prevents the same article appearing multiple times
                # when different queries return it.
                if url not in candidates_by_url:
                    candidates_by_url[url] = candidate

    all_candidates = list(candidates_by_url.values())

    logger.info(
        "Discovered %d unique candidates across %d topics "
        "(RSS fetched=%d, RSS assigned=%d, RSS unmatched=%d, "
        "search results inspected=%d).",
        len(all_candidates),
        len(topics),
        len(rss_candidates),
        rss_assigned,
        rss_unmatched,
        search_count,
    )

    return all_candidates