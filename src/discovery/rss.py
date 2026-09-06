"""RSS/Atom feed discovery provider."""
from __future__ import annotations

import logging
from typing import Dict, List

logger = logging.getLogger("news_bot.discovery.rss")

# Stable, currently maintained public feeds. Reuters' legacy feeds endpoint
# is intentionally not used because it has become unreliable.
RSS_FEEDS: List[str] = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://www.theguardian.com/world/rss",
    "https://rss.dw.com/syndication/feeds/RSS_eng_Aravot.12055-cb.html",
]


def _feed_topic_hint(feed_url: str) -> str:
    url = feed_url.lower()
    if "bbc" in url or "aljazeera" in url or "guardian.com/world" in url or "rss.dw.com" in url:
        return "topic_international_affairs"
    return ""


def fetch_rss_candidates(feeds: List[str] | None = None, limit_per_feed: int = 15) -> List[Dict]:
    """Return normalized raw candidates with a conservative topic hint."""
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
            if getattr(parsed, "bozo", False):
                logger.warning("RSS feed reported a parse issue: %s", feed_url)
            hint = _feed_topic_hint(feed_url)
            for entry in parsed.entries[:limit_per_feed]:
                candidates.append({
                    "title": entry.get("title", "").strip(),
                    "url": entry.get("link", "").strip(),
                    "published_at": entry.get("published", "") or entry.get("updated", ""),
                    "summary": entry.get("summary", "").strip(),
                    "feed_topic_hint": hint,
                })
        except Exception as exc:  # noqa: BLE001
            logger.warning("RSS fetch failed for %s: %s", feed_url, exc)
            continue
    return candidates
