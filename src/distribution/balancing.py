"""Network balancing: mildly discourage one site from dominating the day's
output, without forcing artificial equal quotas (spec section 27)."""
from __future__ import annotations

from typing import Dict


def balance_penalty(website_id: str, current_counts: Dict[str, int], weight: float = 0.15) -> float:
    """Return a score PENALTY (0-100 scale) proportional to how many
    articles this site already has in the current run, relative to others.
    Pure editorial relevance still dominates the final score."""
    if not current_counts:
        return 0.0
    total = sum(current_counts.values()) or 1
    site_count = current_counts.get(website_id, 0)
    share = site_count / total
    # Penalize disproportionately high share; grows superlinearly past 25%.
    if share <= 0.25:
        return 0.0
    return min(100.0, (share - 0.25) * 100 * weight * 4)
