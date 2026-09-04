"""Controlled topic rotation engine (spec section 6).

Selects a subset of topics each run instead of scanning all ~60 topics
every day, using recency-since-last-processed + priority + a controlled
randomness factor so the same topics aren't picked every single day.
Breaking-news topics (flagged externally) can always override rotation.
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional

from src.database.repository import Repository
from src.utils.time import hours_since


def select_topics_for_run(
    all_topics: List[Dict],
    repo: Repository,
    min_topics: int = 15,
    max_topics: int = 35,
    randomness_factor: float = 0.3,
    seed: Optional[int] = None,
) -> List[Dict]:
    rng = random.Random(seed)
    active_topics = [t for t in all_topics if t.get("active", True)]

    def rotation_weight(topic: Dict) -> float:
        last_processed = repo.get_topic_last_processed(topic["id"])
        staleness_hours = hours_since(last_processed) if last_processed else 999.0
        base = topic.get("priority", 5) * min(staleness_hours, 240) / 24.0
        jitter = rng.uniform(1 - randomness_factor, 1 + randomness_factor)
        return base * jitter

    weighted = sorted(active_topics, key=rotation_weight, reverse=True)
    count = min(max(min_topics, len(weighted) // 2), max_topics, len(weighted))
    selected = weighted[:count]

    for topic in selected:
        repo.touch_topic(topic["id"], topic["name"])

    return selected


def merge_breaking_news_topics(selected: List[Dict], all_topics: List[Dict],
                                breaking_topic_ids: List[str]) -> List[Dict]:
    """Breaking news overrides rotation: always include flagged topics."""
    selected_ids = {t["id"] for t in selected}
    by_id = {t["id"]: t for t in all_topics}
    for tid in breaking_topic_ids:
        if tid in by_id and tid not in selected_ids:
            selected.append(by_id[tid])
            selected_ids.add(tid)
    return selected
