"""Thin wrapper around the Blogger API v3 REST endpoints actually used by
this project (create draft post, list recent posts for duplicate checks).
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

import requests

from src.blogger.auth import get_access_token
from src.utils.retry import retry_with_backoff

logger = logging.getLogger("news_bot.blogger.client")

BASE_URL = "https://www.googleapis.com/blogger/v3"


class BloggerClient:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def _headers(self) -> Dict:
        token = get_access_token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def create_draft(self, blog_id: str, title: str, content_html: str) -> Optional[Dict]:
        """Create a DRAFT post (isDraft=true). Never publishes automatically."""
        if self.dry_run:
            logger.info("[DRY RUN] Would create Blogger draft on blog %s: %s", blog_id, title)
            return {"id": "dry-run-id", "url": "https://example.blogspot.com/dry-run"}

        def _call():
            resp = requests.post(
                f"{BASE_URL}/blogs/{blog_id}/posts/",
                params={"isDraft": "true"},
                headers=self._headers(),
                json={"title": title, "content": content_html},
                timeout=20,
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"Blogger draft creation failed ({resp.status_code}): {resp.text[:300]}")
            return resp.json()

        try:
            return retry_with_backoff(_call, max_attempts=3)
        except Exception as exc:  # noqa: BLE001
            logger.error("Blogger draft creation failed for blog %s: %s", blog_id, exc)
            return None

    def list_recent_posts(self, blog_id: str, max_results: int = 20) -> List[Dict]:
        if self.dry_run:
            return []

        def _call():
            resp = requests.get(
                f"{BASE_URL}/blogs/{blog_id}/posts",
                params={"maxResults": max_results, "status": "draft,live"},
                headers=self._headers(),
                timeout=20,
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"Blogger list posts failed ({resp.status_code}): {resp.text[:300]}")
            return resp.json().get("items", [])

        try:
            return retry_with_backoff(_call, max_attempts=2)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not list recent Blogger posts for blog %s: %s", blog_id, exc)
            return []
