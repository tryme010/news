"""Deterministic pre-AI scoring rules: cheap heuristics applied BEFORE any
AI verification call, to control cost (spec section 40: cost control /
staged pipeline). Only candidates that pass this cheap filter get sent to
the (more expensive) AI verifier.
"""
from __future__ import annotations

from typing import Dict, List

SENSITIVE_KEYWORDS = [
    "اتهام", "وفاة", "مقتل", "فضيحة", "احتيال", "اعتقال",
    "accusation", "death", "killed", "scandal", "fraud", "arrest", "allegation",
]


def is_sensitive(title: str, summary: str = "") -> bool:
    text = f"{title} {summary}".lower()
    return any(kw in text for kw in SENSITIVE_KEYWORDS)


def cheap_prefilter(candidate_group: List[Dict], min_sources: int = 1,
                     min_avg_credibility: float = 0.3) -> Dict:
    """Return a dict with a pass/fail decision and reasoning, without any AI call."""
    sources = candidate_group
    if not sources:
        return {"passes": False, "reason": "no_sources"}

    unique_domains = {s.get("domain", "") for s in sources if s.get("domain")}
    avg_credibility = sum(s.get("credibility_score", 0.0) for s in sources) / len(sources)

    title = sources[0].get("title", "")
    summary = sources[0].get("summary", "")
    sensitive = is_sensitive(title, summary)

    required_sources = 2 if sensitive else min_sources
    if len(unique_domains) < required_sources and len(sources) < required_sources:
        return {
            "passes": False,
            "reason": f"insufficient_source_diversity (need {required_sources}, have {len(unique_domains)})",
            "sensitive": sensitive,
        }
    if avg_credibility < min_avg_credibility:
        return {"passes": False, "reason": "low_avg_credibility", "sensitive": sensitive}

    return {"passes": True, "reason": "ok", "sensitive": sensitive, "avg_credibility": avg_credibility}
