"""Time helpers, kept UTC-consistent across the whole pipeline."""
from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def utcnow_iso() -> str:
    return utcnow().isoformat()


def hours_since(iso_timestamp: str) -> float:
    ts = datetime.fromisoformat(iso_timestamp)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    delta = utcnow() - ts
    return delta.total_seconds() / 3600.0
