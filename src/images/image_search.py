"""Search an approved, licensed stock-photo provider (e.g. Unsplash,
Pexels) for an editorial image. Never scrapes Google Images (spec #24).

Requires IMAGE_SEARCH_API_KEY / IMAGE_SEARCH_PROVIDER env vars. Returns
None if not configured or nothing suitable is found, so the caller can
fall back to a generated/generic editorial image.
"""
from __future__ import annotations

import logging
import os
from typing import Dict, Optional

import requests

from src.utils.retry import retry_with_backoff

logger = logging.getLogger("news_bot.images.search")


def search_licensed_image(query: str) -> Optional[Dict]:
    provider = os.environ.get("IMAGE_SEARCH_PROVIDER", "").strip().lower()
    api_key = os.environ.get("IMAGE_SEARCH_API_KEY", "").strip()

    if provider == "unsplash" and api_key:
        return _search_unsplash(query, api_key)
    if provider == "pexels" and api_key:
        return _search_pexels(query, api_key)

    logger.info("No image search provider configured; will use fallback image.")
    return None


def _search_unsplash(query: str, api_key: str) -> Optional[Dict]:
    def _call():
        resp = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": query, "per_page": 1},
            headers={"Authorization": f"Client-ID {api_key}"},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            return None
        photo = results[0]
        return {
            "image_url": photo["urls"]["regular"],
            "source": "unsplash",
            "license": "unsplash_license",
            "credit": photo.get("user", {}).get("name", "Unsplash"),
        }

    try:
        return retry_with_backoff(_call, max_attempts=2)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Unsplash search failed: %s", exc)
        return None


def _search_pexels(query: str, api_key: str) -> Optional[Dict]:
    def _call():
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            params={"query": query, "per_page": 1},
            headers={"Authorization": api_key},
            timeout=15,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if not photos:
            return None
        photo = photos[0]
        return {
            "image_url": photo["src"]["large"],
            "source": "pexels",
            "license": "pexels_license",
            "credit": photo.get("photographer", "Pexels"),
        }

    try:
        return retry_with_backoff(_call, max_attempts=2)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Pexels search failed: %s", exc)
        return None
