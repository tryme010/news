"""Web search discovery provider.

Real implementation stub that calls a configurable search API (e.g. Bing
News Search, SerpAPI, NewsAPI, Google CSE). Provide credentials via
SEARCH_API_KEY / SEARCH_PROVIDER env vars. If none are configured, this
provider returns an empty list rather than failing the whole pipeline
(other discovery providers, e.g. RSS, can still contribute candidates).
"""
from __future__ import annotations

import logging
import os
from typing import Dict, List

import requests

from src.utils.retry import retry_with_backoff

logger = logging.getLogger("news_bot.discovery.search")


def search_news(query: str, language: str = "ar", limit: int = 10) -> List[Dict]:
    provider = os.environ.get("SEARCH_PROVIDER", "").strip().lower()
    api_key = os.environ.get("SEARCH_API_KEY", "").strip()

    if not provider or not api_key:
        logger.info("SEARCH_PROVIDER/SEARCH_API_KEY not configured; skipping web search for '%s'.", query)
        return []

    if provider == "newsapi":
        return _search_newsapi(query, api_key, language, limit)
    if provider == "bing":
        return _search_bing(query, api_key, limit)

    logger.warning("Unknown SEARCH_PROVIDER '%s'; skipping.", provider)
    return []


def _search_newsapi(query: str, api_key: str, language: str, limit: int) -> List[Dict]:
    def _call():
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={"q": query, "language": language, "pageSize": limit, "sortBy": "publishedAt"},
            headers={"X-Api-Key": api_key},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "title": a.get("title", ""),
                "url": a.get("url", ""),
                "published_at": a.get("publishedAt", ""),
                "summary": a.get("description", "") or "",
            }
            for a in data.get("articles", [])
        ]

    try:
        return retry_with_backoff(_call)
    except Exception as exc:  # noqa: BLE001
        logger.warning("NewsAPI search failed for '%s': %s", query, exc)
        return []


def _search_bing(query: str, api_key: str, limit: int) -> List[Dict]:
    def _call():
        resp = requests.get(
            "https://api.bing.microsoft.com/v7.0/news/search",
            params={"q": query, "count": limit},
            headers={"Ocp-Apim-Subscription-Key": api_key},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "title": a.get("name", ""),
                "url": a.get("url", ""),
                "published_at": a.get("datePublished", ""),
                "summary": a.get("description", "") or "",
            }
            for a in data.get("value", [])
        ]

    try:
        return retry_with_backoff(_call)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Bing search failed for '%s': %s", query, exc)
        return []
