"""Build an event fingerprint from core entities + event type + location +
time bucket + core action, so the same underlying event reported by many
sources collapses into ONE event (spec section 15).
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Iterable, List

from src.deduplication.normalizer import normalize_title

STOPWORDS_AR = {"في", "من", "الى", "إلى", "على", "عن", "مع", "و", "ال", "هذا", "هذه"}
STOPWORDS_EN = {"the", "a", "an", "of", "in", "on", "at", "to", "for", "and", "with"}


def _keywords(text: str, limit: int = 6) -> List[str]:
    normalized = normalize_title(text)
    tokens = [t for t in normalized.split() if t not in STOPWORDS_AR and t not in STOPWORDS_EN and len(t) > 2]
    # keep most distinctive (longest) tokens first, capped
    tokens = sorted(set(tokens), key=len, reverse=True)
    return tokens[:limit]


def _time_bucket(event_time: str | None, bucket_hours: int = 24) -> str:
    if not event_time:
        return "unknown"
    try:
        dt = datetime.fromisoformat(event_time)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        bucket_index = int(dt.timestamp() // (bucket_hours * 3600))
        return str(bucket_index)
    except Exception:  # noqa: BLE001
        return "unknown"


def build_fingerprint(
    title: str,
    entities: Iterable[str] | None = None,
    location: str = "",
    event_time: str | None = None,
) -> str:
    """entities + event type/core action (from title keywords) + location + time bucket."""
    entity_part = "|".join(sorted(e.strip().lower() for e in (entities or []) if e.strip()))
    keyword_part = "|".join(_keywords(title))
    location_part = normalize_title(location)
    time_part = _time_bucket(event_time)

    raw = f"{entity_part}::{keyword_part}::{location_part}::{time_part}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
