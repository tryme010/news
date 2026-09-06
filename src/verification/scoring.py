"""Deterministic pre-AI scoring rules.

Cheap heuristics run before AI verification to control cost while avoiding
unnecessary rejection of ordinary news from a single credible source.
"""
from __future__ import annotations

from typing import Dict, List


SENSITIVE_KEYWORDS = [
    # Arabic
    "اتهام",
    "اتهامات",
    "وفاة",
    "مقتل",
    "قتيل",
    "قتلى",
    "فضيحة",
    "احتيال",
    "اعتقال",
    "اعتقل",
    "موقوف",
    "اختلاس",
    "فساد",
    "إدانة",
    "اغتيال",
    "انفجار",
    "هجوم",
    "إصابة",
    "إصابات",

    # English
    "accusation",
    "accused",
    "death",
    "dead",
    "killed",
    "killing",
    "scandal",
    "fraud",
    "arrest",
    "arrested",
    "allegation",
    "allegations",
    "corruption",
    "murder",
    "assassination",
    "explosion",
    "attack",
    "injured",
    "injuries",
]


def is_sensitive(title: str, summary: str = "") -> bool:
    text = f"{title} {summary}".lower()
    return any(keyword in text for keyword in SENSITIVE_KEYWORDS)


def _unique_domains(candidate_group: List[Dict]) -> set[str]:
    return {
        str(source.get("domain", "")).strip().lower()
        for source in candidate_group
        if source.get("domain")
    }


def cheap_prefilter(
    candidate_group: List[Dict],
    min_sources: int = 1,
    min_avg_credibility: float = 0.3,
) -> Dict:
    """Return a cheap pass/fail decision before calling the AI verifier."""
    if not candidate_group:
        return {
            "passes": False,
            "reason": "no_sources",
            "sensitive": False,
        }

    unique_domains = _unique_domains(candidate_group)

    credibility_values = [
        float(source.get("credibility_score", 0.0))
        for source in candidate_group
    ]
    avg_credibility = (
        sum(credibility_values) / len(credibility_values)
        if credibility_values
        else 0.0
    )

    title = candidate_group[0].get("title", "")
    summary = candidate_group[0].get("summary", "")
    sensitive = is_sensitive(title, summary)

    # Sensitive stories require independent source diversity before
    # spending an AI verification call.
    required_sources = 2 if sensitive else max(1, min_sources)
    credible_domains = {
        str(source.get("domain", "")).strip().lower()
        for source in candidate_group
        if source.get("domain") and int(source.get("source_tier", 4)) <= 3
    }

    if len(unique_domains) < required_sources:
        return {
            "passes": False,
            "reason": (
                "insufficient_source_diversity "
                f"(need {required_sources}, have {len(unique_domains)})"
            ),
            "sensitive": sensitive,
            "unique_source_count": len(unique_domains),
            "credible_source_count": len(credible_domains),
            "avg_credibility": avg_credibility,
        }

    if sensitive and len(credible_domains) < 2:
        return {
            "passes": False,
            "reason": (
                "sensitive_story_requires_2_independent_tier1_3_domains "
                f"(have {len(credible_domains)})"
            ),
            "sensitive": True,
            "unique_source_count": len(unique_domains),
            "credible_source_count": len(credible_domains),
            "avg_credibility": avg_credibility,
        }

    if avg_credibility < min_avg_credibility:
        return {
            "passes": False,
            "reason": "low_avg_credibility",
            "sensitive": sensitive,
            "unique_source_count": len(unique_domains),
            "avg_credibility": avg_credibility,
        }

    return {
        "passes": True,
        "reason": "ok",
        "sensitive": sensitive,
        "unique_source_count": len(unique_domains),
        "avg_credibility": avg_credibility,
    }