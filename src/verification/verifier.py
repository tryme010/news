"""AI-assisted verification of a candidate event group.

Runs AFTER the cheap prefilter (scoring.py) to control AI cost. Produces
the fields needed to populate the Event model and gate article generation.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, List

from src.ai.base import AIProvider
from src.verification.scoring import cheap_prefilter

logger = logging.getLogger("news_bot.verification")

STATUS_THRESHOLDS = [
    (40, "reject"),
    (60, "weak"),
    (75, "review"),
    (90, "good"),
    (101, "strong"),
]


def score_to_status(score: float) -> str:
    for threshold, status in STATUS_THRESHOLDS:
        if score < threshold:
            return status
    return "strong"


def _load_prompt_template() -> str:
    with open("config/prompts/verification.txt", "r", encoding="utf-8") as f:
        return f.read()


def verify_event_group(candidate_group: List[Dict], ai: AIProvider,
                        min_score_to_publish: int = 60) -> Dict:
    """Returns a dict describing verification outcome for one event group."""
    prefilter = cheap_prefilter(candidate_group)
    if not prefilter["passes"]:
        return {
            "verification_score": 0,
            "recommended_status": "reject",
            "reason": prefilter["reason"],
            "is_sensitive": prefilter.get("sensitive", False),
            "independent_source_count": 0,
        }

    sources_payload = [
        {
            "url": s.get("url"),
            "title": s.get("title"),
            "summary": s.get("summary", "")[:500],
            "domain": s.get("domain"),
            "tier": s.get("source_tier"),
            "published_at": s.get("published_at"),
        }
        for s in candidate_group
    ]
    event_payload = {
        "title": candidate_group[0].get("title"),
        "sources": sources_payload,
        "is_sensitive_heuristic": prefilter.get("sensitive", False),
    }

    template = _load_prompt_template()
    prompt = f"{template}\n\nEVENT DATA:\n{json.dumps(event_payload, ensure_ascii=False)}"

    try:
        result = ai.verify(prompt)
    except Exception as exc:  # noqa: BLE001
        logger.warning("AI verification failed, falling back to reject: %s", exc)
        return {
            "verification_score": 0,
            "recommended_status": "reject",
            "reason": f"ai_error: {exc}",
            "is_sensitive": prefilter.get("sensitive", False),
            "independent_source_count": 0,
        }

    score = float(result.get("verification_score", 0))
    status = result.get("recommended_status") or score_to_status(score)

    if not result.get("is_real_event", False) or not result.get("sufficient_source_support", False):
        status = "reject"
        score = min(score, 39)

    return {
        "verification_score": score,
        "recommended_status": status,
        "reason": result.get("confidence_notes", ""),
        "is_sensitive": result.get("is_sensitive", prefilter.get("sensitive", False)),
        "independent_source_count": result.get("independent_source_count", len(candidate_group)),
        "passes_publish_bar": score >= min_score_to_publish and status not in ("reject", "weak"),
    }
