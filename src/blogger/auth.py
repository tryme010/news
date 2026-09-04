"""Blogger API v3 OAuth2 authentication.

Uses a long-lived refresh token (obtained once manually per
BLOGGER_SETUP.md) to mint short-lived access tokens at runtime. Never
commit GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / GOOGLE_REFRESH_TOKEN —
these must come from GitHub Secrets / environment variables only.
"""
from __future__ import annotations

import os

import requests

from src.utils.retry import retry_with_backoff

TOKEN_URL = "https://oauth2.googleapis.com/token"


class BloggerAuthError(RuntimeError):
    pass


def get_access_token() -> str:
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN", "").strip()

    if not (client_id and client_secret and refresh_token):
        raise BloggerAuthError(
            "Missing Blogger/Google OAuth credentials. Set GOOGLE_CLIENT_ID, "
            "GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN (see BLOGGER_SETUP.md)."
        )

    def _call():
        resp = requests.post(
            TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            raise BloggerAuthError(f"Token refresh failed ({resp.status_code}): {resp.text[:300]}")
        return resp.json()["access_token"]

    return retry_with_backoff(_call, max_attempts=3)
