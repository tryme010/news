"""RSS/Atom feed discovery provider.

Real implementation using `feedparser`. Configure feed URLs in
config/settings.json (or extend RSS_FEEDS below) — this module performs
actual HTTP fetches when run in an environment with outbound internet
access (e.g. GitHub Actions), which the sandbox this was authored in does
not have.
"""
from __future__ import annotations

import logging
from typing import Dict, List

logger = logging.getLogger("news_bot.discovery.rss")

# Starter set; extend freely. Kept small and editable rather than
# hardcoded deep in logic (per spec section 7: "do not depend on one
# website").
RSS_FEEDS: List[str] = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://feeds.reuters.com/reuters/topNews",
]


def fetch_rss_candidates(feeds: List[str] | None = None, limit_per_feed: int = 15) -> List[Dict]:
    """Return a list of raw candidate dicts: {title, url, published_at, summary}."""
    try:
        import feedparser
    except ImportError:
        logger.warning("feedparser not installed; skipping RSS discovery.")
        return []

    feeds = feeds or RSS_FEEDS
    candidates: List[Dict] = []
    for feed_url in feeds:
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries[:limit_per_feed]:
                candidates.append({
                    "title": entry.get("title", "").strip(),
                    "url": entry.get("link", "").strip(),
                    "published_at": entry.get("published", "") or entry.get("updated", ""),
                    "summary": entry.get("summary", "").strip(),
                })
        except Exception as exc:  # noqa: BLE001
            logger.warning("RSS fetch failed for %s: %s", feed_url, exc)
            continue
    return candidates
