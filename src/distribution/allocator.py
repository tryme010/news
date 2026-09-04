"""Decide which website(s) receive a given verified event, and ensure
genuinely distinct editorial angles rather than copies (spec section 26).
"""
from __future__ import annotations

from typing import Dict, List

from src.distribution.balancing import balance_penalty
from src.distribution.scorer import score_event_for_all_websites


def allocate_event_to_websites(
    event: Dict,
    websites: List[Dict],
    current_counts: Dict[str, int],
    min_relevance_score: float = 55,
    max_sites_per_event: int = 4,
    balance_weight: float = 0.15,
) -> List[Dict]:
    scored = score_event_for_all_websites(event, websites)

    adjusted = []
    for entry in scored:
        penalty = balance_penalty(entry["website_id"], current_counts, balance_weight)
        adjusted_score = max(0.0, entry["score"] - penalty)
        if adjusted_score >= min_relevance_score:
            adjusted.append({**entry, "adjusted_score": adjusted_score})

    adjusted.sort(key=lambda x: x["adjusted_score"], reverse=True)
    return adjusted[:max_sites_per_event]
