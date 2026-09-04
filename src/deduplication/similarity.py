"""Semantic/lexical similarity helpers for catching near-duplicate events
that don't share an identical fingerprint (e.g. slightly different entity
extraction), plus grouping of raw candidates into event clusters.
"""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Dict, List

from src.deduplication.fingerprint import build_fingerprint
from src.deduplication.normalizer import normalize_title
from src.utils.time import hours_since


def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_title(a), normalize_title(b)).ratio()


def group_candidates_into_events(candidates: List[Dict], similarity_threshold: float = 0.82,
                                  time_window_hours: float = 36) -> List[List[Dict]]:
    """Cluster raw candidates that likely describe the same real-world event.

    Two candidates are grouped together if:
      - they share an identical fingerprint, OR
      - their titles are highly similar AND they were published within the
        configured time window of each other.
    This directly implements spec section 15/16: many sources -> one event.
    """
    groups: List[List[Dict]] = []

    for cand in candidates:
        cand["_fingerprint"] = build_fingerprint(
            cand.get("title", ""),
            cand.get("entities", []),
            cand.get("country", "") or cand.get("region", ""),
            cand.get("published_at"),
        )
        placed = False
        for group in groups:
            rep = group[0]
            same_fp = rep["_fingerprint"] == cand["_fingerprint"]
            similar_title = title_similarity(rep.get("title", ""), cand.get("title", "")) >= similarity_threshold
            close_in_time = True
            if rep.get("published_at") and cand.get("published_at"):
                try:
                    close_in_time = abs(hours_since(rep["published_at"]) - hours_since(cand["published_at"])) <= time_window_hours
                except Exception:  # noqa: BLE001
                    close_in_time = True
            if same_fp or (similar_title and close_in_time):
                group.append(cand)
                placed = True
                break
        if not placed:
            groups.append([cand])

    return groups
