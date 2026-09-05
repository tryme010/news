"""AI-assisted verification of candidate event groups.

Runs after the cheap deterministic prefilter and uses AI as the final
verification authority before article generation.
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


def _independent_source_count(candidate_group: List[Dict]) -> int:
    """Count distinct source domains."""
    return len({
        str(source.get("domain", "")).strip().lower()
        for source in candidate_group
        if source.get("domain")
    })


def verify_event_group(
    candidate_group: List[Dict],
    ai: AIProvider,
    min_score_to_publish: int = 60,
) -> Dict:
    """Return verification outcome for one candidate event group."""

    prefilter = cheap_prefilter(candidate_group)

    if not prefilter["passes"]:
        return {
            "verification_score": 0,
            "recommended_status": "reject",
            "reason": prefilter["reason"],
            "is_sensitive": prefilter.get("sensitive", False),
            "independent_source_count": prefilter.get(
                "unique_source_count", 0
            ),
            "passes_publish_bar": False,
        }

    independent_count = _independent_source_count(candidate_group)

    sources_payload = [
        {
            "url": source.get("url"),
            "title": source.get("title"),
            "summary": source.get("summary", "")[:500],
            "domain": source.get("domain"),
            "tier": source.get("source_tier"),
            "published_at": source.get("published_at"),
        }
        for source in candidate_group
    ]

    event_payload = {
        "title": candidate_group[0].get("title"),
        "sources": sources_payload,
        "is_sensitive_heuristic": prefilter.get("sensitive", False),
        "independent_source_count": independent_count,
    }

    template = _load_prompt_template()

    prompt = (
        f"{template}\n\n"
        "EVENT DATA:\n"
        f"{json.dumps(event_payload, ensure_ascii=False)}"
    )

    try:
        result = ai.verify(prompt)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "AI verification failed, falling back to reject: %s",
            exc,
        )
        return {
            "verification_score": 0,
            "recommended_status": "reject",
            "reason": f"ai_error: {exc}",
            "is_sensitive": prefilter.get("sensitive", False),
            "independent_source_count": independent_count,
            "passes_publish_bar": False,
        }

    try:
        score = float(result.get("verification_score", 0))
    except (TypeError, ValueError):
        score = 0.0

    score = max(0.0, min(100.0, score))

    status = result.get("recommended_status")
    if status not in {"reject", "weak", "review", "good", "strong"}:
        status = score_to_status(score)

    is_real_event = bool(result.get("is_real_event", False))
    sufficient_support = bool(
        result.get("sufficient_source_support", False)
    )

    # AI must confirm both reality and source support.
    if not is_real_event or not sufficient_support:
        status = "reject"
        score = min(score, 39)

    # Sensitive stories must retain independent-source protection even if
    # the model accidentally returns an optimistic recommendation.
    if prefilter.get("sensitive", False) and independent_count < 2:
        status = "reject"
        score = min(score, 39)

    passes_publish_bar = (
        score >= min_score_to_publish
        and status not in {"reject", "weak"}
    )

    return {
        "verification_score": score,
        "recommended_status": status,
        "reason": result.get("confidence_notes", ""),
        "is_sensitive": result.get(
            "is_sensitive",
            prefilter.get("sensitive", False),
        ),
        "independent_source_count": independent_count,
        "passes_publish_bar": passes_publish_bar,
    }