"""Thin wrapper around the Blogger API v3 endpoints used by the project."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

import requests

from src.blogger.auth import get_access_token
from src.utils.retry import retry_with_backoff

logger = logging.getLogger("news_bot.blogger.client")

BASE_URL = "https://www.googleapis.com/blogger/v3"


class BloggerPermissionError(RuntimeError):
    """Raised when the OAuth identity cannot access a target Blogger blog."""


class BloggerClient:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._access_token: Optional[str] = None

    def _headers(self) -> Dict[str, str]:
        if not self._access_token:
            self._access_token = get_access_token()
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    def _reset_token(self) -> None:
        self._access_token = None

    def _raise_for_blogger_error(self, resp: requests.Response, action: str, blog_id: str) -> None:
        if resp.status_code < 400:
            return
        if resp.status_code == 401:
            self._reset_token()
            raise RuntimeError(
                f"Blogger {action} failed (401) for blog {blog_id}: access token rejected."
            )
        if resp.status_code == 403:
            raise BloggerPermissionError(
                f"Blogger {action} failed (403) for blog {blog_id}: caller does not have permission. "
                "The OAuth account must have edit/admin access to this Blogger blog and the "
                "refresh token must include https://www.googleapis.com/auth/blogger."
            )
        raise RuntimeError(
            f"Blogger {action} failed ({resp.status_code}) for blog {blog_id}: {resp.text[:500]}"
        )

    def check_blog_access(self, blog_id: str) -> bool:
        """Verify that the OAuth identity can read the target blog before writing."""
        if self.dry_run:
            return True

        def _call():
            resp = requests.get(
                f"{BASE_URL}/blogs/{blog_id}",
                headers=self._headers(),
                timeout=20,
            )
            self._raise_for_blogger_error(resp, "blog access check", blog_id)
            return True

        try:
            return bool(retry_with_backoff(_call, max_attempts=2))
        except Exception as exc:  # noqa: BLE001
            logger.error("Blogger access check failed for blog %s: %s", blog_id, exc)
            return False

    def create_draft(self, blog_id: str, title: str, content_html: str) -> Optional[Dict]:
        """Create a DRAFT post (isDraft=true). Never publishes automatically."""
        if self.dry_run:
            logger.info("[DRY RUN] Would create Blogger draft on blog %s: %s", blog_id, title)
            return {"id": "dry-run-id", "url": "https://example.blogspot.com/dry-run"}

        # Do this once per blog so a bad blog ID / account permission is diagnosed
        # before we spend time generating more articles for the same destination.
        if not self.check_blog_access(blog_id):
            return None

        def _call():
            resp = requests.post(
                f"{BASE_URL}/blogs/{blog_id}/posts",
                params={"isDraft": "true"},
                headers=self._headers(),
                json={"title": title, "content": content_html},
                timeout=20,
            )
            self._raise_for_blogger_error(resp, "draft creation", blog_id)
            return resp.json()

        try:
            return retry_with_backoff(_call, max_attempts=2)
        except BloggerPermissionError as exc:
            logger.error("%s", exc)
            return None
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
            self._raise_for_blogger_error(resp, "list posts", blog_id)
            return resp.json().get("items", [])

        try:
            return retry_with_backoff(_call, max_attempts=2)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not list recent Blogger posts for blog %s: %s", blog_id, exc)
            return []
