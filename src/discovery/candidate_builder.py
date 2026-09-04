"""Combine all discovery providers into a normalized candidate list for a
set of topics, then hand off to deduplication/verification.
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


def discover_candidates(topics: List[Dict], demo_mode: bool = False, demo_fixtures: List[Dict] | None = None) -> List[Dict]:
    """Return a flat list of raw candidates, each tagged with the topic that
    surfaced it and basic source classification.
    """
    if demo_mode:
        return demo_fixtures or []

    all_candidates: List[Dict] = []
    rss_candidates = fetch_rss_candidates()

    for topic in topics:
        topic_candidates: List[Dict] = []

        for item in rss_candidates:
            topic_candidates.append(item)

        for query in build_queries(topic)[:4]:
            topic_candidates.extend(search_news(query))

        for item in topic_candidates:
            url = item.get("url", "")
            if not url:
                continue
            normalized = normalize_url(url)
            classification = classify_domain(normalized)
            all_candidates.append({
                **item,
                "url": normalized,
                "topic_id": topic["id"],
                "domain": classification["domain"],
                "source_tier": classification["tier"],
                "credibility_score": classification["credibility_score"],
            })

    logger.info("Discovered %d raw candidates across %d topics.", len(all_candidates), len(topics))
    return all_candidates
