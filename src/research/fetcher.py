"""Fetch full page content for important candidates that need deeper
research before verification/writing (beyond the search snippet)."""
from __future__ import annotations

import logging

import requests

from src.utils.retry import retry_with_backoff

logger = logging.getLogger("news_bot.research.fetcher")

USER_AGENT = "NewsAutomationBot/1.0 (+https://example.com/bot-info)"


def fetch_page(url: str, timeout: int = 15) -> str | None:
    def _call():
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        resp.raise_for_status()
        return resp.text

    try:
        return retry_with_backoff(_call, max_attempts=2)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None
